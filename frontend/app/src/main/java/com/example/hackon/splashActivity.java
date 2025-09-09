package com.example.hackon;

import android.content.Intent;
import android.os.Bundle;
import android.util.Log;
import android.widget.Button;
import android.widget.Toast;

import androidx.activity.EdgeToEdge;
import androidx.appcompat.app.AppCompatActivity;
import androidx.core.graphics.Insets;
import androidx.core.view.ViewCompat;
import androidx.core.view.WindowInsetsCompat;

import com.google.firebase.auth.FirebaseAuth;
import com.google.firebase.auth.FirebaseUser;
import com.google.firebase.firestore.FirebaseFirestore;

import java.util.Objects;

public class splashActivity extends AppCompatActivity {

    Button getStartedButton;
    FirebaseAuth mAuth;
    FirebaseFirestore db;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        EdgeToEdge.enable(this);

        mAuth = FirebaseAuth.getInstance();
        db = FirebaseFirestore.getInstance();
        FirebaseUser currentUser = mAuth.getCurrentUser();

        if (currentUser != null) {
            String userId = currentUser.getUid();
            db.collection("users2").document(userId).get()
                    .addOnSuccessListener(documentSnapshot -> {
                        if (documentSnapshot.exists()) {
                            String role = documentSnapshot.getString("Role");
                            Intent intentLogin;
                            if (Objects.equals(role, "User")) {
                                intentLogin = new Intent(splashActivity.this, userHomeActivity.class);
                            } else {
                                intentLogin = new Intent(splashActivity.this, deliveryHomeActivity.class);
                            }
                            Toast.makeText(splashActivity.this, "Login Successful", Toast.LENGTH_SHORT).show();
                            startActivity(intentLogin);
                            finish();
                        } else {
                            showSplashContent();
                        }
                    })
                    .addOnFailureListener(e -> {
                        Toast.makeText(splashActivity.this, "Failed to fetch role", Toast.LENGTH_SHORT).show();
                        showSplashContent();
                    });
        } else {
            showSplashContent();
        }
    }

    private void showSplashContent() {
        setContentView(R.layout.activity_splash);
        ViewCompat.setOnApplyWindowInsetsListener(findViewById(R.id.main), (v, insets) -> {
            Insets systemBars = insets.getInsets(WindowInsetsCompat.Type.systemBars());
            v.setPadding(systemBars.left, systemBars.top, systemBars.right, systemBars.bottom);
            return insets;
        });

        getStartedButton = findViewById(R.id.getStartedBtn);
        getStartedButton.setOnClickListener(v -> startActivity(new Intent(this, loginActivity.class)));
        Log.d("shiwal2510", "onCreate: showing splash content");
    }

}