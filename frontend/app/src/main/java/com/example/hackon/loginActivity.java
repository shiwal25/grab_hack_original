package com.example.hackon;

import android.content.Intent;
import android.os.Bundle;
import android.text.TextUtils;
import android.util.Log;
import android.view.View;
import android.widget.Button;
import android.widget.EditText;
import android.widget.TextView;
import android.widget.Toast;

import androidx.activity.EdgeToEdge;
import androidx.annotation.NonNull;
import androidx.appcompat.app.AppCompatActivity;
import androidx.core.graphics.Insets;
import androidx.core.view.ViewCompat;
import androidx.core.view.WindowInsetsCompat;

import com.google.android.gms.tasks.OnCompleteListener;
import com.google.android.gms.tasks.Task;
import com.google.firebase.auth.AuthResult;
import com.google.firebase.auth.FirebaseAuth;
import com.google.firebase.auth.FirebaseUser;
import com.google.firebase.firestore.FirebaseFirestore;

import java.util.Objects;

public class loginActivity extends AppCompatActivity {

    EditText email, password;
    TextView register;
    Button login;
    Intent intentRegister;
    FirebaseAuth mAuth;
    FirebaseFirestore db;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        EdgeToEdge.enable(this);
        setContentView(R.layout.activity_login);

        ViewCompat.setOnApplyWindowInsetsListener(findViewById(R.id.main), (v, insets) -> {
            Insets systemBars = insets.getInsets(WindowInsetsCompat.Type.systemBars());
            v.setPadding(systemBars.left, systemBars.top, systemBars.right, systemBars.bottom);
            return insets;
        });

        mAuth = FirebaseAuth.getInstance();
        db = FirebaseFirestore.getInstance();

        email = findViewById(R.id.log_email);
        password = findViewById(R.id.log_pass);
        register = findViewById(R.id.logToReg);
        login = findViewById(R.id.log_button);

        // Navigate to register activity
        intentRegister = new Intent(this, registerActivity.class);
        register.setOnClickListener(v -> startActivity(intentRegister));

        // Login button click
        login.setOnClickListener(v -> {
            String mail = email.getText().toString().trim();
            String pass = password.getText().toString().trim();

            if (TextUtils.isEmpty(mail)) {
                Toast.makeText(loginActivity.this, "Email cannot be empty", Toast.LENGTH_SHORT).show();
                return;
            }
            if (TextUtils.isEmpty(pass)) {
                Toast.makeText(loginActivity.this, "Password cannot be empty", Toast.LENGTH_SHORT).show();
                return;
            }

            // Sign in with Firebase Auth
            mAuth.signInWithEmailAndPassword(mail, pass)
                    .addOnCompleteListener(new OnCompleteListener<AuthResult>() {
                        @Override
                        public void onComplete(@NonNull Task<AuthResult> task) {
                            if (task.isSuccessful()) {
                                FirebaseUser user = mAuth.getCurrentUser();
                                if (user == null) {
                                    Toast.makeText(loginActivity.this, "User not found", Toast.LENGTH_SHORT).show();
                                    return;
                                }

                                String userId = user.getUid();

                                // Fetch user role from Firestore
                                db.collection("users2").document(userId).get()
                                        .addOnSuccessListener(documentSnapshot -> {
                                            if (documentSnapshot.exists()) {
                                                String role = documentSnapshot.getString("Role");
                                                Intent intentLogin;
                                                if (Objects.equals(role, "User")) {
                                                    intentLogin = new Intent(loginActivity.this, userHomeActivity.class);
                                                } else {
                                                    intentLogin = new Intent(loginActivity.this, deliveryHomeActivity.class);
                                                }

                                                Toast.makeText(loginActivity.this, "Login Successful", Toast.LENGTH_SHORT).show();
                                                startActivity(intentLogin);
                                                finish();
                                                finishAfterTransition();
                                            } else {
                                                Toast.makeText(loginActivity.this, "User role not found", Toast.LENGTH_SHORT).show();
                                            }
                                        })
                                        .addOnFailureListener(e ->
                                                Toast.makeText(loginActivity.this, "Failed to fetch role", Toast.LENGTH_SHORT).show()
                                        );

                            } else {
                                Toast.makeText(loginActivity.this, "Authentication failed.", Toast.LENGTH_SHORT).show();
                            }
                        }
                    });
        });
    }
}
