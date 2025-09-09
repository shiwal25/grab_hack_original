package com.example.hackon;

import android.content.Intent;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.speech.RecognizerIntent;
import android.speech.SpeechRecognizer;
import android.view.View;
import android.widget.Button;
import android.widget.EditText;
import android.widget.ImageButton;
import android.widget.LinearLayout;
import android.widget.TextView;
import android.widget.Toast;

import androidx.activity.EdgeToEdge;
import androidx.appcompat.app.AppCompatActivity;
import androidx.core.graphics.Insets;
import androidx.core.view.ViewCompat;
import androidx.core.view.WindowInsetsCompat;

import com.google.android.material.bottomsheet.BottomSheetDialog;
import com.google.firebase.auth.FirebaseAuth;

import org.json.JSONException;
import org.json.JSONObject;

import java.util.Locale;

import io.socket.client.Socket;

public class deliveryHomeActivity extends AppCompatActivity {

    EditText editText;
    ImageButton sendScenarioBtn, sendAudioBtn;
    SpeechRecognizer speechRecognizer;
    Intent speechRecognizerIntent;
    Socket socket;
    Handler mainHandler = new Handler(Looper.getMainLooper());
    boolean sessionStarted = false;
    Button logoutButton;
    Intent intent;
    LinearLayout messagesContainer;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        EdgeToEdge.enable(this);
        setContentView(R.layout.activity_delivery_home);

        // Edge-to-edge padding
        ViewCompat.setOnApplyWindowInsetsListener(findViewById(R.id.main), (v, insets) -> {
            Insets sysBars = insets.getInsets(WindowInsetsCompat.Type.systemBars());
            v.setPadding(sysBars.left, sysBars.top, sysBars.right, sysBars.bottom);
            return insets;
        });

        // UI elements
        editText = findViewById(R.id.scenarioText);
        sendScenarioBtn = findViewById(R.id.sendScenarioBtn);
        sendAudioBtn = findViewById(R.id.sendAudioBtn);
        logoutButton = findViewById(R.id.logoutButton);
        messagesContainer = findViewById(R.id.messagesContainer);
        intent = new Intent(deliveryHomeActivity.this, splashActivity.class);

        // Speech recognizer setup
        speechRecognizer = SpeechRecognizer.createSpeechRecognizer(this);
        speechRecognizerIntent = new Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH);
        speechRecognizerIntent.putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM);
        speechRecognizerIntent.putExtra(RecognizerIntent.EXTRA_LANGUAGE, Locale.getDefault());

        // Socket
        socket = SocketManager.getSocket();

        // Start session immediately
        startSession();

        // Logout button
        logoutButton.setOnClickListener(v -> {
            FirebaseAuth.getInstance().signOut();
            Toast.makeText(this, "Sign out Successful", Toast.LENGTH_SHORT).show();
            finish();
            startActivity(intent);
        });

        // Voice input
        sendAudioBtn.setOnClickListener(v -> {
            sendAudioBtn.setImageResource(R.drawable.ic_microphoneoff);
            speechRecognizer.setRecognitionListener(new recognitionListener(findViewById(R.id.main), speechRecognizer));
            speechRecognizer.startListening(speechRecognizerIntent);
        });

        // Send user input via scenario button
        sendScenarioBtn.setOnClickListener(v -> {
            String situation = editText.getText().toString().trim();
            if (situation.isEmpty()) {
                Toast.makeText(this, "Please enter a situation", Toast.LENGTH_SHORT).show();
                return;
            }

            sendUserInput(situation);
        });

        // Listen for agent_response
        socket.on("agent_response", args -> {
            if (args.length > 0) {
                try {
                    JSONObject res = (JSONObject) args[0];

                    // Driver-targeted messages (no bubble - just toast for confirmation)
                    if (res.has("type") && "request_user_input".equals(res.getString("type"))) {
                        String target = res.optString("target", "");
                        String prompt = res.optString("prompt", "");

                        if ("driver".equalsIgnoreCase(target)) {
                            mainHandler.post(() -> Toast.makeText(this, "Driver prompt: " + prompt, Toast.LENGTH_LONG).show());
                        } else if ("recipient".equalsIgnoreCase(target)) {
                            // Show message bubble for recipient messages
                            mainHandler.post(() -> addMessageBubble(prompt, false)); // false = received message
                        }
                    }

                    // Agent events - show in modal bottom sheet
                    if (res.has("event")) {
                        String event = res.getString("event");
                        mainHandler.post(() -> {
                            if ("grabexpress".equalsIgnoreCase(event)) {
                                showEventModal("GrabExpress Service", "Switching to GrabExpress flow", () -> {
                                    Intent i = new Intent(deliveryHomeActivity.this, grabExpressActivity.class);
                                    startActivity(i);
                                    finish();
                                });
                            } else if ("grabcar".equalsIgnoreCase(event)) {
                                showEventModal("GrabCar Service", "Switching to GrabCar flow", () -> {
                                    Intent i = new Intent(deliveryHomeActivity.this, grabCarActivity.class);
                                    startActivity(i);
                                    finish();
                                });
                            } else {
                                showEventModal("Unknown Event", "Event: " + event, null);
                            }
                        });
                    }

                } catch (Exception e) {
                    e.printStackTrace();
                }
            }
        });
    }

    private void addMessageBubble(String message, boolean isUserMessage) {
        if (messagesContainer == null) return;

        TextView messageView = new TextView(this);
        messageView.setText(message);
        messageView.setPadding(32, 24, 32, 24);
        messageView.setTextSize(14);

        LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.WRAP_CONTENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
        );
        params.setMargins(16, 8, 16, 8);

        if (isUserMessage) {
            // User message - align right, blue background
            params.gravity = android.view.Gravity.END;
            messageView.setBackgroundResource(android.R.drawable.dialog_holo_light_frame);
            messageView.setTextColor(getResources().getColor(android.R.color.white, null));
        } else {
            // Received message - align left, gray background  
            params.gravity = android.view.Gravity.START;
            messageView.setBackgroundResource(android.R.drawable.dialog_holo_dark_frame);
            messageView.setTextColor(getResources().getColor(android.R.color.black, null));
        }

        messageView.setLayoutParams(params);
        messagesContainer.addView(messageView);
    }

    private void showEventModal(String title, String message, Runnable onProceed) {
        BottomSheetDialog bottomSheetDialog = new BottomSheetDialog(this);
        View bottomSheetView = getLayoutInflater().inflate(R.layout.bottom_sheet_event, null);

        TextView titleView = bottomSheetView.findViewById(R.id.eventTitle);
        TextView messageView = bottomSheetView.findViewById(R.id.eventMessage);
        Button proceedButton = bottomSheetView.findViewById(R.id.proceedButton);
        Button cancelButton = bottomSheetView.findViewById(R.id.cancelButton);

        titleView.setText(title);
        messageView.setText(message);

        proceedButton.setOnClickListener(v -> {
            bottomSheetDialog.dismiss();
            if (onProceed != null) {
                onProceed.run();
            }
        });

        cancelButton.setOnClickListener(v -> bottomSheetDialog.dismiss());

        bottomSheetDialog.setContentView(bottomSheetView);
        bottomSheetDialog.show();
    }

    private void startSession() {
        if (!sessionStarted) {
            try {
                JSONObject startData = new JSONObject();
                startData.put("user_id", "unique_user_id");
                startData.put("location", "Lucknow, Uttar Pradesh, India");
                socket.emit("start_session", startData);
                sessionStarted = true;
                Toast.makeText(this, "Session started", Toast.LENGTH_SHORT).show();
            } catch (JSONException e) {
                e.printStackTrace();
            }
        }
    }

    private void sendUserInput(String input) {
        try {
            // Add user message bubble
            addMessageBubble(input, true);

            JSONObject inputData = new JSONObject();
            inputData.put("input", input);
            socket.emit("send_user_input", inputData);
            editText.setText("");
        } catch (JSONException e) {
            e.printStackTrace();
        }
    }

    @Override
    protected void onDestroy() {
        super.onDestroy();
        if (socket != null) socket.off("agent_response");
    }
}
