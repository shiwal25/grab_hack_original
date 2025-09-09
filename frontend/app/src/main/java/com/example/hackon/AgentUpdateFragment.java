package com.example.hackon;

import android.os.Bundle;
import android.os.CountDownTimer;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.TextView;

import androidx.annotation.NonNull;
import androidx.annotation.Nullable;
import androidx.fragment.app.DialogFragment;

public class AgentUpdateFragment extends DialogFragment {

    private TextView messageTextView;
    private CountDownTimer timer;

    public AgentUpdateFragment() {
        // Required empty constructor
    }

    @Nullable
    @Override
    public View onCreateView(@NonNull LayoutInflater inflater, @Nullable ViewGroup container,
                             @Nullable Bundle savedInstanceState) {
        View view = inflater.inflate(R.layout.fragment_agent_update, container, false);
        messageTextView = view.findViewById(R.id.messageTextView);
        return view;
    }

    /**
     * Call this whenever a new message arrives.
     * @param message Message text from agent
     */
    public void showMessage(String message) {
        if (messageTextView != null) {
            messageTextView.setText(message);
        }

        // Cancel previous timer if fragment is already open
        if (timer != null) {
            timer.cancel();
        }

        // Auto-close fragment after 30 seconds
        timer = new CountDownTimer(30000, 1000) {
            @Override
            public void onTick(long millisUntilFinished) { }

            @Override
            public void onFinish() {
                dismissAllowingStateLoss();
            }
        }.start();
    }

    @Override
    public void onDestroyView() {
        super.onDestroyView();
        if (timer != null) {
            timer.cancel();
        }
    }
}
