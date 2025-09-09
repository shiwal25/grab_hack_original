package com.example.hackon;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.content.SharedPreferences;
import android.os.Bundle;
import android.util.Log;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.EditText;
import android.widget.ImageButton;
import android.widget.Toast;

import androidx.annotation.NonNull;
import androidx.fragment.app.Fragment;
import androidx.localbroadcastmanager.content.LocalBroadcastManager;

import com.google.firebase.FirebaseException;
import com.google.firebase.auth.FirebaseAuth;
import com.google.firebase.auth.PhoneAuthCredential;
import com.google.firebase.auth.PhoneAuthOptions;
import com.google.firebase.auth.PhoneAuthProvider;
import com.google.firebase.firestore.DocumentSnapshot;
import com.google.firebase.firestore.FirebaseFirestore;

import java.util.ArrayList;
import java.util.concurrent.TimeUnit;

public class otpFragment extends Fragment {

    private EditText otp;
    private FirebaseAuth mAuth;
    private String verificationID;
    FirebaseFirestore db = FirebaseFirestore.getInstance();
    String phone;

    public otpFragment() { }

    @Override
    public void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        mAuth = FirebaseAuth.getInstance();
        db.collection("phoneNo")
                .orderBy("timestamp")
                .addSnapshotListener((snapshots, e) -> {
                    if (e != null) return;
//                    for (DocumentSnapshot doc : snapshots) {
//                        phone = doc.getString("phoneNo");
//                    }
                    assert snapshots != null;
                    phone = snapshots.getDocuments().get(0).getString("phoneNo");
                    Log.d("Helooooo", "onCreate: "+phone);
                    phone = "+91" + phone;
                    Log.d("Helooooo", "onCreate: "+phone);
                    assert phone != null;
                    if (!phone.isEmpty()) {
                        startPhoneVerification(phone);
                    } else {
                        Toast.makeText(getContext(), "Phone number missing", Toast.LENGTH_SHORT).show();
                    }

                });
    }

    @Override
    public View onCreateView(LayoutInflater inflater, ViewGroup container,
                             Bundle savedInstanceState) {

        View view = inflater.inflate(R.layout.fragment_otp, container, false);

        // Initialize views
        ImageButton closeButton = view.findViewById(R.id.closeButton);
        Button submitButton = view.findViewById(R.id.submitButton);
        otp = view.findViewById(R.id.otp);

        // Close button listener
        closeButton.setOnClickListener(v -> {
            getParentFragmentManager().popBackStack();
        });

        // Submit button listener
        submitButton.setOnClickListener(v -> {
            String otpText = otp.getText().toString().trim();
            if (otpText.isEmpty()) {
                otp.setError("Enter OTP");
                return;
            }
            if (verificationID == null) {
                Log.e("OTP", "No verification ID. OTP not sent yet?");
                return;
            }

            PhoneAuthCredential credential = PhoneAuthProvider.getCredential(verificationID, otpText);
            mAuth.signInWithCredential(credential)
                    .addOnCompleteListener(task -> {
                        if (task.isSuccessful()) {
                            Log.d("OTP", "OTP verified successfully!");
                            Intent intent = new Intent(getActivity(), deliveryHomeActivity.class);
                            startActivity(intent);
                            requireActivity().finish();
                        } else {
                            Log.e("OTP", "Verification failed", task.getException());
                        }
                    });
        });

        return view;
    }

    @Override
    public void onDestroy() {
        super.onDestroy();

    }

    @Override
    public void onDestroyView() {
        super.onDestroyView();
    }

    private void startPhoneVerification(String phone) {
        PhoneAuthOptions options = PhoneAuthOptions.newBuilder(mAuth)
                .setPhoneNumber(phone)
                .setTimeout(60L, TimeUnit.SECONDS)
                .setActivity(requireActivity())
                .setCallbacks(new PhoneAuthProvider.OnVerificationStateChangedCallbacks() {
                    @Override
                    public void onVerificationCompleted(@NonNull PhoneAuthCredential credential) {
                        // Auto-retrieval (rare)
                    }

                    @Override
                    public void onVerificationFailed(@NonNull FirebaseException e) {
                        Log.e("OTP", "Verification failed: " + e.getMessage());
                    }

                    @Override
                    public void onCodeSent(@NonNull String verificationId,
                                           @NonNull PhoneAuthProvider.ForceResendingToken token) {
                        Log.d("OTP", "OTP sent to number!");
                        verificationID = verificationId;
                    }
                })
                .build();

        PhoneAuthProvider.verifyPhoneNumber(options);
    }
}
