package com.example.hackon;

import android.content.pm.PackageManager;
import android.location.Location;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.util.Log;

import androidx.activity.EdgeToEdge;
import androidx.annotation.NonNull;
import androidx.appcompat.app.AppCompatActivity;
import androidx.core.app.ActivityCompat;
import androidx.core.content.ContextCompat;
import androidx.core.graphics.Insets;
import androidx.core.view.ViewCompat;

import android.widget.AutoCompleteTextView;
import android.widget.Button;
import android.widget.EditText;
import android.widget.ImageButton;
import android.widget.Toast;

import androidx.core.view.WindowInsetsCompat;
import androidx.fragment.app.Fragment;
import androidx.fragment.app.FragmentManager;
import androidx.fragment.app.FragmentTransaction;
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
import com.google.android.libraries.places.api.model.AutocompletePrediction;
import com.google.android.libraries.places.api.model.Place;
import com.google.android.libraries.places.api.net.FetchPlaceRequest;
import com.google.android.libraries.places.api.net.PlacesClient;
import com.google.firebase.firestore.DocumentSnapshot;
import com.google.firebase.firestore.FirebaseFirestore;

import org.json.JSONException;
import org.json.JSONObject;

import java.util.ArrayList;
import java.util.List;

import okhttp3.OkHttpClient;
import okhttp3.Request;
import okhttp3.WebSocket;
import okhttp3.WebSocketListener;
import okio.ByteString;

public class grabExpressActivity extends AppCompatActivity implements OnMapReadyCallback {

    MapView mapView;
    PlacesClient placesClient;
    boolean locationPermissionGranted;
    private static final int PERMISSIONS_REQUEST_ACCESS_FINE_LOCATION = 1;
    private Location lastKnownLocation;
    LatLng  defaultLocation = new LatLng(28.7041, 77.1025); ;
    GoogleMap googleMap;
    private FusedLocationProviderClient fusedLocationProviderClient;
    private Marker marker;
    RecyclerView recyclerView;
    Button deliveredButton;
    ArrayList<Message> messages;
    rvAdapter adapter2;
    FirebaseFirestore db;
    Handler mainHandler = new Handler(Looper.getMainLooper());


    AutoCompleteTextView searchLocation;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        EdgeToEdge.enable(this);
        setContentView(R.layout.activity_grab_express);
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
        messages = new ArrayList<>();
        adapter2 = new rvAdapter(messages, false, getSupportFragmentManager());
        recyclerView.setLayoutManager(new LinearLayoutManager(this));
        recyclerView.setAdapter(adapter2);
        db  = FirebaseFirestore.getInstance();
        deliveredButton = findViewById(R.id.deliveredButton);

        searchLocation = findViewById(R.id.searchLocation);
        PlacesAutoCompleteAdapter adapter = new PlacesAutoCompleteAdapter(this, placesClient);
        searchLocation.setAdapter(adapter);

        searchLocation.setOnItemClickListener((parent, view, position, id) -> {
            AutocompletePrediction prediction = adapter.getPrediction(position);
            String placeId = prediction.getPlaceId();

            placesClient.fetchPlace(
                    FetchPlaceRequest.builder(
                                    placeId, List.of(Place.Field.LAT_LNG, Place.Field.NAME))
                            .build()
            ).addOnSuccessListener(response -> {
                Place place = response.getPlace();
                LatLng newLocation = place.getLatLng();

                if (newLocation != null) {
                    if (marker != null) {
                        marker.setPosition(newLocation);
                        marker.setTitle(place.getName());
                    } else {
                        marker = googleMap.addMarker(new MarkerOptions().position(newLocation).title(place.getName()));
                    }
                    googleMap.animateCamera(CameraUpdateFactory.newLatLngZoom(newLocation, 17f));

                    JSONObject locationData = new JSONObject();
                    try {
//                        locationData.put("type", "request_user_input");
//                        locationData.put("target", "driver");
                        locationData.put("input", place.getName());
                        SocketManager.getSocket().emit("send_user_input", locationData);
                        SocketManager.getSocket().off("agent_response");

                        Toast.makeText(grabExpressActivity.this, "Location sent: " + place.getName(), Toast.LENGTH_SHORT).show();
//                        SocketManager.getSocket().disconnect();
//                        SocketManager.getSocket().off(); // remove all listeners to clean up
                    } catch (JSONException e) {
                        e.printStackTrace();
                    }
                }
            }).addOnFailureListener(e -> Log.e("GrabExpress", "Place not found: " + e.getMessage()));
            Log.e("GrabExpress", "Place not found: " );

        });

        deliveredButton.setOnClickListener(v ->{

            FragmentManager fragmentManager = getSupportFragmentManager();
            FragmentTransaction fragmentTransaction = fragmentManager.beginTransaction();
            otpFragment OTPFRAGMENT = new otpFragment();
            fragmentTransaction.replace(R.id.otp_container, OTPFRAGMENT);
            fragmentTransaction.addToBackStack(null);
            fragmentTransaction.commit();
        });

        db.collection("messages")
                .get()
                .addOnSuccessListener(querySnapshot -> {
                    for (DocumentSnapshot doc : querySnapshot) {
                        doc.getReference().delete();
                    }
                });

        db.collection("messages")
                .orderBy("timestamp")
                .addSnapshotListener((snapshots, e) -> {
                    if (e != null) return;

                    ArrayList<Message> newMessages = new ArrayList<>();
                    for (DocumentSnapshot doc : snapshots) {
                        String text = doc.getString("text");
                        if (text != null) {
                            newMessages.add(new Message(text, "user", "message"));
                            Log.d("FIRESTORE_MSG", "Received: " + text);
                        }
                    }

                    mainHandler.post(() -> {
                        adapter2.setMessages(newMessages); // adapter clears + adds internally
                        recyclerView.scrollToPosition(newMessages.size() - 1);
                    });
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
        if(locationPermissionGranted){
            getDeviceLocation();
        }
        updateLocationUI();

    }
    
    public void updateLocationUI(){
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
            } catch (SecurityException e)  {
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
                            // Set the map's camera position to the current location of the device.
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
        } catch (SecurityException e)  {
            Log.e("Exception: %s", e.getMessage(), e);
        }
    }

}