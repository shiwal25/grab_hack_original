package com.example.hackon;

import android.content.Intent;
import android.content.pm.PackageManager;
import android.location.Location;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.util.Log;
import android.widget.Button;
import android.widget.EditText;
import android.widget.ImageButton;
import android.widget.Toast;

import androidx.activity.EdgeToEdge;
import androidx.annotation.NonNull;
import androidx.appcompat.app.AppCompatActivity;
import androidx.core.app.ActivityCompat;
import androidx.core.content.ContextCompat;
import androidx.core.graphics.Insets;
import androidx.core.view.ViewCompat;
import androidx.core.view.WindowInsetsCompat;
import androidx.recyclerview.widget.LinearLayoutManager;
import androidx.recyclerview.widget.RecyclerView;

import com.google.android.gms.location.FusedLocationProviderClient;
import com.google.android.gms.location.LocationServices;
import com.google.android.gms.maps.CameraUpdateFactory;
import com.google.android.gms.maps.GoogleMap;
import com.google.android.gms.maps.MapView;
import com.google.android.gms.maps.OnMapReadyCallback;
import com.google.android.gms.maps.model.LatLng;
import com.google.android.gms.maps.model.Marker;
import com.google.android.gms.maps.model.MarkerOptions;
import com.google.android.gms.tasks.OnCompleteListener;
import com.google.android.gms.tasks.Task;
import com.google.android.libraries.places.api.Places;
import com.google.android.libraries.places.api.net.PlacesClient;
import com.google.android.material.bottomsheet.BottomSheetDialogFragment;
import com.google.firebase.auth.FirebaseAuth;
import com.google.firebase.firestore.FirebaseFirestore;
import com.google.gson.Gson;

import org.json.JSONException;
import org.json.JSONObject;

import java.net.URISyntaxException;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashMap;
import java.util.Map;

import io.socket.client.IO;
import io.socket.client.Socket;

public class userHomeActivity extends AppCompatActivity implements OnMapReadyCallback {

    MapView mapView;
    PlacesClient placesClient;
    boolean locationPermissionGranted;
    private static final int PERMISSIONS_REQUEST_ACCESS_FINE_LOCATION = 1;
    private Location lastKnownLocation;
    LatLng defaultLocation = new LatLng(28.7041, 77.1025);
    GoogleMap googleMap;
    private FusedLocationProviderClient fusedLocationProviderClient;
    private Marker marker;
    RecyclerView recyclerView;
    Button logoutButton;
    ArrayList<Message> messages = new ArrayList<>();
    Intent intent;
    String phoneNo;
    Map<String, Object> data = new HashMap<>();
    Map<String, Object> data2 = new HashMap<>();
    Gson gson = new Gson();
    EditText messageInput;
    ImageButton sendButton;
    rvAdapter adapter;
    Handler mainHandler = new Handler(Looper.getMainLooper());

    private Socket socket;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        EdgeToEdge.enable(this);
        setContentView(R.layout.activity_user_home);
        ViewCompat.setOnApplyWindowInsetsListener(findViewById(R.id.main), (v, insets) -> {
            Insets systemBars = insets.getInsets(WindowInsetsCompat.Type.systemBars());
            v.setPadding(systemBars.left, systemBars.top, systemBars.right, systemBars.bottom);
            return insets;
        });

        getLocationPermission();
        mapView = findViewById(R.id.mapView);
        mapView.onCreate(savedInstanceState);
        mapView.getMapAsync(this);
        Places.initialize(getApplicationContext(), BuildConfig.MAPS_API_KEY);
        placesClient = Places.createClient(this);
        fusedLocationProviderClient = LocationServices.getFusedLocationProviderClient(this);
        recyclerView = findViewById(R.id.delExpChat);
        recyclerView.setLayoutManager(new LinearLayoutManager(this));
        adapter = new rvAdapter(messages, true, getSupportFragmentManager());
        messageInput = findViewById(R.id.replyType);
        sendButton = findViewById(R.id.replySend);
        recyclerView.setAdapter(adapter);
        logoutButton = findViewById(R.id.logoutButton);
        intent = new Intent(this, splashActivity.class);
        FirebaseFirestore db = FirebaseFirestore.getInstance();

        initSocketIO(db);

        logoutButton.setOnClickListener(v -> {
            FirebaseAuth.getInstance().signOut();
            Toast.makeText(userHomeActivity.this, "Sign out Successful", Toast.LENGTH_SHORT).show();
            finish();
            startActivity(intent);
            finish();
        });

        sendButton.setOnClickListener(v -> {
            String text = messageInput.getText().toString().trim();
            if (text.length() == 10 && (text.charAt(0) == '6' || text.charAt(0) == '7' || text.charAt(0) == '8' || text.charAt(0) == '9')) {
                data2.put("phoneNo", text);
                data2.put("timestamp", System.currentTimeMillis());
                phoneNo = "+91" + text;
                db.collection("phoneNo").add(data2)
                        .addOnSuccessListener(documentReference -> Log.d("FIREBASE", "phoneNo added!"))
                        .addOnFailureListener(e -> Log.w("FIREBASE", "Error", e));
            }
            if (!text.isEmpty()) {
                Message msg = new Message(text, "user", "");
                adapter.addMessage(msg);
                recyclerView.scrollToPosition(messages.size() - 1);

                if (socket != null && socket.connected()) {
                    try {
                        JSONObject jsonMessage = new JSONObject();
                        jsonMessage.put("input", text);
                        socket.emit("send_user_input", jsonMessage);
                    } catch (JSONException e) {
                        e.printStackTrace();
                    }
                }
                messageInput.setText("");

                data.put("sender", "user");
                data.put("text", text);
                data.put("timestamp", System.currentTimeMillis());
                db.collection("messages")
                        .add(data)
                        .addOnSuccessListener(docRef -> Log.d("FIREBASE", "Message sent!"))
                        .addOnFailureListener(e -> Log.w("FIREBASE", "Error", e));
            }
        });
    }

    @Override
    public void onMapReady(@NonNull GoogleMap googleMap) {
        this.googleMap = googleMap;
        marker = googleMap.addMarker(new MarkerOptions()
                .position(defaultLocation)
                .title("Marker"));
        googleMap.setTrafficEnabled(true);
        if (locationPermissionGranted) {
            getDeviceLocation();
        } else {
            googleMap.moveCamera(CameraUpdateFactory.newLatLngZoom(defaultLocation, 17f));
        }
    }

    private void getLocationPermission() {
        if (ContextCompat.checkSelfPermission(this.getApplicationContext(), android.Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED) {
            locationPermissionGranted = true;
        } else {
            ActivityCompat.requestPermissions(this, new String[]{android.Manifest.permission.ACCESS_FINE_LOCATION}, PERMISSIONS_REQUEST_ACCESS_FINE_LOCATION);
        }
    }

    @Override
    public void onRequestPermissionsResult(int requestCode, @NonNull String[] permissions, @NonNull int[] grantResults) {
        locationPermissionGranted = false;
        if (requestCode == PERMISSIONS_REQUEST_ACCESS_FINE_LOCATION) {
            if (grantResults.length > 0 && grantResults[0] == PackageManager.PERMISSION_GRANTED) {
                locationPermissionGranted = true;
            }
        } else {
            super.onRequestPermissionsResult(requestCode, permissions, grantResults);
        }
        if (locationPermissionGranted) {
            getDeviceLocation();
        }
        updateLocationUI();
    }

    public void updateLocationUI() {
        if (mapView == null) {
            return;
        }
        try {
            if (locationPermissionGranted) {
                googleMap.setMyLocationEnabled(true);
                googleMap.getUiSettings().setMyLocationButtonEnabled(true);
                getDeviceLocation();
            } else {
                googleMap.setMyLocationEnabled(false);
                googleMap.getUiSettings().setMyLocationButtonEnabled(false);
                lastKnownLocation = null;
            }
        } catch (SecurityException e) {
            Log.e("Exception: %s", e.getMessage());
        }
    }

    private void getDeviceLocation() {
        try {
            if (locationPermissionGranted) {
                Task<Location> locationResult = fusedLocationProviderClient.getLastLocation();
                locationResult.addOnCompleteListener(this, new OnCompleteListener<Location>() {
                    @Override
                    public void onComplete(@NonNull Task<Location> task) {
                        if (task.isSuccessful()) {
                            lastKnownLocation = task.getResult();
                            if (lastKnownLocation != null) {
                                googleMap.moveCamera(CameraUpdateFactory.newLatLngZoom(
                                        new LatLng(lastKnownLocation.getLatitude(),
                                                lastKnownLocation.getLongitude()), 17f));

                                if (marker != null) {
                                    marker.setPosition(new LatLng(lastKnownLocation.getLatitude(),
                                            lastKnownLocation.getLongitude()));
                                }
                            }
                        } else {
                            marker.setPosition(defaultLocation);
                            Log.d("TAG", "Current location is null. Using defaults.");
                            Log.e("TAG", "Exception: %s", task.getException());
                            googleMap.moveCamera(CameraUpdateFactory
                                    .newLatLngZoom(defaultLocation, 17f));
                            googleMap.getUiSettings().setMyLocationButtonEnabled(false);
                        }
                    }
                });
            }
        } catch (SecurityException e) {
            Log.e("Exception: %s", e.getMessage(), e);
        }
    }

    private void initSocketIO(FirebaseFirestore db) {
        try {
            socket = IO.socket("http://10.0.2.2:8080");

            socket.on(Socket.EVENT_CONNECT, args -> {
                Log.d("SOCKET", "Connected to server!");

                // Send initial recipient info only
                try {
                    JSONObject startData = new JSONObject();
                    startData.put("user_id", "unique_user_id"); // your user ID
                    startData.put("location", "Lucknow, Uttar Pradesh, India"); // dynamically fetched or fixed
                    startData.put("situation", "GrabExpress"); // optional
                    socket.emit("start_session", startData);
                    Log.d("SOCKET", "Sent start_session: " + startData.toString());
                } catch (JSONException e) {
                    e.printStackTrace();
                }
            });

            socket.on("agent_response", args -> {
                if (args.length > 0) {
                    mainHandler.post(() -> {
                        try {
                            JSONObject jsonResponse = (JSONObject) args[0];
                            String type = jsonResponse.optString("type", "");
                            String target = jsonResponse.optString("target", "");

                            // Store agent_event chain data for later use
                            if (type.equals("agent_event")) {
                                String event = jsonResponse.optString("event", "");
                                if (event.equals("agent_action")) {
                                    String tool = jsonResponse.optString("tool", "");
                                    String toolInput = jsonResponse.optString("tool_input", "");
                                    String log = jsonResponse.optString("log", "");

                                    // Store chain data for the next message
                                    String chainData = "Tool: " + tool + "\n\nTool Input:\n" + toolInput + "\n\nLog Details:\n" + log;
                                    // We'll use this when the next request_user_input comes
                                    storeChainData(chainData);
                                }
                            }

                            // Only display recipient request_user_input as message with chain capability
                            if (type.equals("request_user_input") && target.equals("recipient")) {
                                String prompt = jsonResponse.optString("prompt", "");
                                // Remove timeout info from prompt for cleaner display
                                String cleanPrompt = prompt.replaceAll("\\s*\\[\\d+s timeout\\]:>\\s*$", "");

                                // Format locker lists better
                                if (cleanPrompt.contains("Found nearby secure parcel lockers:") ||
                                        cleanPrompt.contains("Please select one by entering the number:")) {
                                    cleanPrompt = formatLockerList(cleanPrompt);
                                }

                                // Create message with chain data (or empty if no chain)
                                String chainData = getStoredChainData();
                                Message msg = new Message(cleanPrompt, "agent", chainData != null ? chainData : "");
                                adapter.addMessage(msg);
                                recyclerView.scrollToPosition(messages.size() - 1);

                                // Clear stored chain data after using it
                                clearStoredChainData();
                            }

                            // Handle info messages that might not have agent_event
                            if (type.equals("info") && target.equals("recipient")) {
                                String message = jsonResponse.optString("message", "");

                                // Format locker lists
                                if (message.contains("Found nearby secure parcel lockers:")) {
                                    message = formatLockerList(message);
                                }

                                Message msg = new Message(message, "agent", "");
                                adapter.addMessage(msg);
                                recyclerView.scrollToPosition(messages.size() - 1);
                            }
                        } catch (Exception e) {
                            Log.e("SOCKET", "Error parsing agent response", e);
                        }
                    });
                }
            });

            socket.on(Socket.EVENT_DISCONNECT, args -> Log.d("SOCKET", "Disconnected from server."))
                    .on(Socket.EVENT_CONNECT_ERROR, args -> Log.e("SOCKET", "Connection error: " + Arrays.toString(args)));

            socket.connect();
        } catch (URISyntaxException e) {
            e.printStackTrace();
        }
    }

    private String storedChainData = null;

    private void storeChainData(String chainData) {
        this.storedChainData = chainData;
    }

    private String getStoredChainData() {
        return storedChainData;
    }

    private void clearStoredChainData() {
        this.storedChainData = null;
    }

    private void showActionModal(String tool, String toolInput, String log) {
        ActionModalFragment modal = ActionModalFragment.newInstance(tool, toolInput, log);
        modal.show(getSupportFragmentManager(), "action_modal");
    }

    private String formatLockerList(String text) {
        // Improved formatting for parcel locker lists using regex
        // 1. Place header on its own line
        // 2. Each numbered item on its own line
        // 3. Footer prompt on its own line

        // First, ensure the header is on its own line
        String formatted = text.replace("Found nearby secure parcel lockers:", "Found nearby secure parcel lockers:\n\n");

        // Now, split each number-dot list item onto its own line (handles no spaces after .)
        formatted = formatted.replaceAll("\\s*(\\d+)\\.\\s*", "\n$1. ");

        // Ensure the footer is double newlined before
        formatted = formatted.replace("Please select one by entering the number:", "\n\nPlease select one by entering the number:");

        // Remove accidental multiple newlines (3+)
        formatted = formatted.replaceAll("\\n{3,}", "\n\n");
        // Trim, but always ensure a newline after the last list item and before the footer
        formatted = formatted.trim();

        return formatted;
    }

    @Override
    protected void onDestroy() {
        super.onDestroy();
        if (socket != null) {
            socket.disconnect();
            socket.off();
        }
    }
}
