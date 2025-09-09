package com.example.hackon;

import android.content.Context;
import android.content.pm.PackageManager;
import android.graphics.Color;
import android.location.Location;
import android.os.AsyncTask;
import android.os.Bundle;
import android.util.Log;
import android.widget.AutoCompleteTextView;
import android.widget.Button;

import androidx.activity.EdgeToEdge;
import androidx.annotation.NonNull;
import androidx.appcompat.app.AppCompatActivity;
import androidx.core.app.ActivityCompat;
import androidx.core.content.ContextCompat;
import androidx.core.graphics.Insets;
import androidx.core.view.ViewCompat;
import androidx.core.view.WindowInsetsCompat;
import androidx.fragment.app.FragmentManager;
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
import com.google.android.gms.maps.model.PolylineOptions;
import com.google.android.gms.tasks.OnCompleteListener;
import com.google.android.gms.tasks.Task;
import com.google.android.libraries.places.api.Places;
import com.google.android.libraries.places.api.model.AutocompletePrediction;
import com.google.android.libraries.places.api.model.Place;
import com.google.android.libraries.places.api.net.FetchPlaceRequest;
import com.google.android.libraries.places.api.net.PlacesClient;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.BufferedInputStream;
import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;

public class grabCarActivity extends AppCompatActivity implements OnMapReadyCallback {

    MapView mapView;
    PlacesClient placesClient;
    boolean locationPermissionGranted;
    private static final int PERMISSIONS_REQUEST_ACCESS_FINE_LOCATION = 1;
    private Location lastKnownLocation;
    LatLng defaultLocation = new LatLng(28.7041, 77.1025); ;
    GoogleMap googleMap;
    private FusedLocationProviderClient fusedLocationProviderClient;
    private Marker marker;
    Button deliveredButton;
    FragmentManager otpFragment;
    AutoCompleteTextView searchDestination;
    AutoCompleteTextView searchSource;
    private LatLng sourceLatLng, destinationLatLng;
    private Marker destinationMarker;
    private AgentUpdateFragment agentFragment;


    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        EdgeToEdge.enable(this);
        setContentView(R.layout.activity_grab_car);
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
        deliveredButton = findViewById(R.id.deliveredButton);
        searchDestination = findViewById(R.id.searchDestination);
        searchSource = findViewById(R.id.searchSource);
        PlacesAutoCompleteAdapter adapter = new PlacesAutoCompleteAdapter(this, placesClient);
        searchSource.setAdapter(adapter);
        searchDestination.setAdapter(adapter);

        searchSource.setOnItemClickListener((parent, view, position, id) -> {
            AutocompletePrediction prediction = adapter.getPrediction(position);
            String placeId = prediction.getPlaceId();
            placesClient.fetchPlace(
                    FetchPlaceRequest.builder(
                                    placeId, List.of(Place.Field.LAT_LNG, Place.Field.NAME))
                            .build()
            ).addOnSuccessListener(response -> {
                Place place = response.getPlace();
                sourceLatLng = place.getLatLng();
                // update marker if needed
                if (sourceLatLng != null) {
                    googleMap.addMarker(new MarkerOptions().position(sourceLatLng).title("Source: " + place.getName()));
                    googleMap.animateCamera(CameraUpdateFactory.newLatLngZoom(sourceLatLng, 14f));
                }
                drawRouteIfPossible();
            });
        });

        // inside searchDestination.setOnItemClickListener()
        searchDestination.setOnItemClickListener((parent, view, position, id) -> {
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
                    //remove old marker, add fresh destination marker
                    if (destinationMarker != null) {
                        destinationMarker.remove();
                    }
                    destinationMarker = googleMap.addMarker(
                            new MarkerOptions().position(newLocation).title(place.getName())
                    );
                    googleMap.animateCamera(CameraUpdateFactory.newLatLngZoom(newLocation, 17f));

            /*
            googleMap.addMarker(new MarkerOptions().position(sourceLatLng).title("Source: " + place.getName()));
            googleMap.animateCamera(CameraUpdateFactory.newLatLngZoom(sourceLatLng, 14f));
            */
                }
                destinationLatLng = newLocation;
                drawRouteIfPossible();
            });
        });


        deliveredButton.setOnClickListener(v ->{

        });
    }

    @Override
    public void onMapReady(@NonNull GoogleMap googleMap) {
        this.googleMap = googleMap;
        googleMap.setTrafficEnabled(true);

        if (locationPermissionGranted) {
            getDeviceLocation(); // move camera only
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

    // inside getDeviceLocation()
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
                                //  NEW CODE (no marker here, just camera move)
                                googleMap.moveCamera(CameraUpdateFactory.newLatLngZoom(
                                        new LatLng(lastKnownLocation.getLatitude(),
                                                lastKnownLocation.getLongitude()), 17f));

                                //  OLD CODE (we don’t want a marker at current location)
                            /*
                            if (marker != null) {
                                marker.setPosition(new LatLng(lastKnownLocation.getLatitude(),
                                        lastKnownLocation.getLongitude()));
                            }
                            */
                            }
                        } else {
                            // keep marker line commented
                            // marker.setPosition(defaultLocation);
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


    private void drawRouteIfPossible() {
        if (sourceLatLng != null && destinationLatLng != null) {
            String url = getDirectionsUrl(sourceLatLng, destinationLatLng);
            new FetchURL(this).execute(url, "driving");
        }
    }

    private String getDirectionsUrl(LatLng origin, LatLng dest) {
        String str_origin = "origin=" + origin.latitude + "," + origin.longitude;
        String str_dest = "destination=" + dest.latitude + "," + dest.longitude;
        String mode = "mode=driving";
        String parameters = str_origin + "&" + str_dest + "&" + mode + "&key=" + BuildConfig.MAPS_API_KEY;
        return "https://maps.googleapis.com/maps/api/directions/json?" + parameters;
    }

    public class FetchURL extends AsyncTask<String, Void, String> {
        Context mContext;

        public FetchURL(Context context) {
            mContext = context;
        }

        @Override
        protected String doInBackground(String... strings) {
            try {
                URL url = new URL(strings[0]);
                HttpURLConnection conn = (HttpURLConnection) url.openConnection();
                conn.connect();
                InputStream in = new BufferedInputStream(conn.getInputStream());
                BufferedReader reader = new BufferedReader(new InputStreamReader(in));
                StringBuilder sb = new StringBuilder();
                String line;
                while ((line = reader.readLine()) != null) {
                    sb.append(line);
                }
                return sb.toString();
            } catch (Exception e) {
                Log.e("FetchURL", "Error: " + e.getMessage());
            }
            return null;
        }

        @Override
        protected void onPostExecute(String result) {
            if (result != null) {
                new TaskParser(mContext).execute(result);
            }
        }
    }

    public class TaskParser extends AsyncTask<String, Void, List<List<HashMap<String, String>>>> {
        Context mContext;

        public TaskParser(Context context) {
            mContext = context;
        }

        @Override
        protected List<List<HashMap<String, String>>> doInBackground(String... strings) {
            JSONObject jsonObject;
            List<List<HashMap<String, String>>> routes = null;
            try {
                jsonObject = new JSONObject(strings[0]);
                DirectionsJSONParser parser = new DirectionsJSONParser();
                routes = parser.parse(jsonObject);
            } catch (Exception e) {
                e.printStackTrace();
            }
            return routes;
        }

        @Override
        protected void onPostExecute(List<List<HashMap<String, String>>> lists) {
            ArrayList<LatLng> points;
            PolylineOptions polylineOptions = null;

            for (List<HashMap<String, String>> path : lists) {
                points = new ArrayList<>();
                polylineOptions = new PolylineOptions();

                for (HashMap<String, String> point : path) {
                    double lat = Double.parseDouble(point.get("lat"));
                    double lng = Double.parseDouble(point.get("lng"));
                    points.add(new LatLng(lat, lng));
                }
                polylineOptions.addAll(points);
                polylineOptions.width(12);
                polylineOptions.color(Color.BLUE);
                polylineOptions.geodesic(true);
            }
            if (polylineOptions != null) {
                ((grabCarActivity)mContext).googleMap.addPolyline(polylineOptions);
            }
        }
    }

    public class DirectionsJSONParser {
        public List<List<HashMap<String,String>>> parse(JSONObject jObject) {
            List<List<HashMap<String, String>>> routes = new ArrayList<>();
            JSONArray jRoutes;
            JSONArray jLegs;
            JSONArray jSteps;

            try {
                jRoutes = jObject.getJSONArray("routes");
                for (int i=0; i<jRoutes.length(); i++) {
                    jLegs = ((JSONObject) jRoutes.get(i)).getJSONArray("legs");
                    List<HashMap<String, String>> path = new ArrayList<>();

                    for (int j=0; j<jLegs.length(); j++) {
                        jSteps = ((JSONObject) jLegs.get(j)).getJSONArray("steps");
                        for (int k=0; k<jSteps.length(); k++) {
                            String polyline = (String)((JSONObject)((JSONObject)jSteps.get(k)).get("polyline")).get("points");
                            List<LatLng> list = decodePoly(polyline);

                            for (LatLng l : list) {
                                HashMap<String, String> hm = new HashMap<>();
                                hm.put("lat", Double.toString(l.latitude));
                                hm.put("lng", Double.toString(l.longitude));
                                path.add(hm);
                            }
                        }
                        routes.add(path);
                    }
                }
            } catch (Exception e) {
                e.printStackTrace();
            }
            return routes;
        }

        private List<LatLng> decodePoly(String encoded) {
            List<LatLng> poly = new ArrayList<>();
            int index = 0, len = encoded.length();
            int lat = 0, lng = 0;

            while (index < len) {
                int b, shift = 0, result = 0;
                do {
                    b = encoded.charAt(index++) - 63;
                    result |= (b & 0x1f) << shift;
                    shift += 5;
                } while (b >= 0x20);
                int dlat = ((result & 1) != 0 ? ~(result >> 1) : (result >> 1));
                lat += dlat;

                shift = 0;
                result = 0;
                do {
                    b = encoded.charAt(index++) - 63;
                    result |= (b & 0x1f) << shift;
                    shift += 5;
                } while (b >= 0x20);
                int dlng = ((result & 1) != 0 ? ~(result >> 1) : (result >> 1));
                lng += dlng;

                LatLng p = new LatLng((((double) lat / 1E5)),
                        (((double) lng / 1E5)));
                poly.add(p);
            }
            return poly;
        }
    }

    private void showAgentMessage(String message) {
        FragmentManager fm = getSupportFragmentManager();

        if (agentFragment == null || !agentFragment.isAdded()) {
            agentFragment = new AgentUpdateFragment();
            agentFragment.show(fm, "agent_update");
        }

        // Update message & reset timer
        agentFragment.showMessage(message);
    }

}