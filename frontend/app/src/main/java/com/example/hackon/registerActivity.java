package com.example.hackon;

import android.content.Intent;
import android.os.Build;
import android.os.Bundle;
import android.util.Log;
import android.view.View;
import android.widget.Button;
import android.widget.EditText;
import android.widget.RadioButton;
import android.widget.RadioGroup;
import android.widget.Toast;

import androidx.activity.EdgeToEdge;
import androidx.annotation.NonNull;
import androidx.appcompat.app.AppCompatActivity;
import androidx.core.graphics.Insets;
import androidx.core.view.ViewCompat;
import androidx.core.view.WindowInsetsCompat;

import com.google.android.gms.tasks.OnCompleteListener;
import com.google.android.gms.tasks.OnFailureListener;
import com.google.android.gms.tasks.OnSuccessListener;
import com.google.android.gms.tasks.Task;
import com.google.firebase.auth.AuthResult;
import com.google.firebase.auth.FirebaseAuth;
import com.google.firebase.auth.FirebaseUser;
import com.google.firebase.firestore.DocumentReference;
import com.google.firebase.firestore.FirebaseFirestore;

import java.util.HashMap;
import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public class registerActivity extends AppCompatActivity {

    EditText regEmail;
    EditText regPass;
    EditText regName;
    Button regButton;
    FirebaseAuth mAuth;
    String userId;
    Intent intent;
    FirebaseFirestore db;
    RadioGroup radioGroup;
    public int validateEmail(String value){
        String pattern = "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$";
        Pattern regex = Pattern.compile(pattern);
        Matcher matcher = regex.matcher(value);
        if (!matcher.matches()) {
            Toast.makeText(this, "Enter a valid Email", Toast.LENGTH_SHORT).show();
            return 0;
        }
        else{
            return 1;
        }
    }

    public int validatePassword(String value) {
        String ans = "";
        if (value.length() < 8) {
            ans = "Password must be at least 8 characters long";
        }
        else if (!value.matches(".*[A-Z].*")) {
            ans = "Password must contain at least one uppercase letter";
        }
        else if (!value.matches(".*[a-z].*")) {
            ans = "Password must contain at least one lowercase letter";
        }
        else if (!value.matches(".*[0-9].*")) {
            ans = "Password must contain at least one digit";
        }
        else if (!value.matches(".*[!@#\\$&*~].*")) {
            ans = "Password must contain at least one special character";
        }

        if(ans.equals("")){
            return 1;
        }
        else{
            Toast.makeText(this,ans, Toast.LENGTH_SHORT).show();
            return 0;
        }
    }
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        EdgeToEdge.enable(this);
        setContentView(R.layout.activity_register);
        ViewCompat.setOnApplyWindowInsetsListener(findViewById(R.id.main), (v, insets) -> {
            Insets systemBars = insets.getInsets(WindowInsetsCompat.Type.systemBars());
            v.setPadding(systemBars.left, systemBars.top, systemBars.right, systemBars.bottom);
            return insets;
        });

        regEmail = findViewById(R.id.reg_mail);
        regPass = findViewById(R.id.reg_password);
        regName = findViewById(R.id.reg_name);
        regButton = findViewById(R.id.reg_button);
        intent = new Intent(this, loginActivity.class);
        mAuth = FirebaseAuth.getInstance();
        db = FirebaseFirestore.getInstance();
        radioGroup = findViewById(R.id.radioGroup);

        regButton.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                String mail = regEmail.getText().toString();
                String name = regName.getText().toString();
                String pass = regPass.getText().toString();
                int m = validateEmail(mail);
                int p = validatePassword(pass);
                int n = 1;

                if(name.isEmpty()){
                    Toast.makeText(registerActivity.this, "Name cannot be empty", Toast.LENGTH_SHORT).show();
                    n = 0 ;
                }

                // Get the checked radio button ID and view here
                int selectedId = radioGroup.getCheckedRadioButtonId();
                if (selectedId == -1) {
                    Toast.makeText(registerActivity.this, "Please select a role", Toast.LENGTH_SHORT).show();
                    return;
                }
                RadioButton role = findViewById(selectedId);
                String roleString = role.getText().toString();

                if (m == 1 && p == 1 && n == 1) {
                    mAuth.createUserWithEmailAndPassword(mail, pass)
                            .addOnCompleteListener(new OnCompleteListener<AuthResult>() {
                                @Override
                                public void onComplete(@NonNull Task<AuthResult> task) {
                                    if (task.isSuccessful()) {
                                        FirebaseUser users = mAuth.getCurrentUser();
                                        Toast.makeText(registerActivity.this, "Account Created", Toast.LENGTH_SHORT).show();

                                        userId = FirebaseAuth.getInstance().getUid();

                                        Map<String, Object> user = new HashMap<>();
                                        user.put("mail", mail);
                                        user.put("name", name);
                                        user.put("ID", userId);
                                        user.put("Role", roleString); // Use the string value

                                        db.collection("users2")
                                                .document(userId)
                                                .set(user)
                                                .addOnSuccessListener(new OnSuccessListener<Void>() {
                                                    @Override
                                                    public void onSuccess(Void unused) {
                                                        Log.d("Shiwal2510", "DocumentSnapshot successfully written! ID: " + userId);
                                                    }
                                                })
                                                .addOnFailureListener(new OnFailureListener() {
                                                    @Override
                                                    public void onFailure(@NonNull Exception e) {
                                                        Log.w("Shiwal2510", "Error adding document", e);
                                                    }
                                                });

                                        startActivity(intent);
                                        finish();

                                    } else {
                                        Toast.makeText(registerActivity.this, "Authentication failed.",
                                                Toast.LENGTH_SHORT).show();
                                    }
                                }
                            });
                }
            }
        });
    }
}