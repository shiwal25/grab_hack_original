package com.example.hackon;

import android.os.Bundle;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.TextView;

import androidx.annotation.NonNull;
import androidx.annotation.Nullable;

import com.google.android.material.bottomsheet.BottomSheetDialogFragment;

public class ActionModalFragment extends BottomSheetDialogFragment {

    private static final String ARG_TOOL = "tool";
    private static final String ARG_TOOL_INPUT = "tool_input";
    private static final String ARG_LOG = "log";

    public static ActionModalFragment newInstance(String tool, String toolInput, String log) {
        ActionModalFragment fragment = new ActionModalFragment();
        Bundle args = new Bundle();
        args.putString(ARG_TOOL, tool);
        args.putString(ARG_TOOL_INPUT, toolInput);
        args.putString(ARG_LOG, log);
        fragment.setArguments(args);
        return fragment;
    }

    @Nullable
    @Override
    public View onCreateView(@NonNull LayoutInflater inflater, @Nullable ViewGroup container, @Nullable Bundle savedInstanceState) {
        return inflater.inflate(R.layout.fragment_action_modal, container, false);
    }

    @Override
    public void onViewCreated(@NonNull View view, @Nullable Bundle savedInstanceState) {
        super.onViewCreated(view, savedInstanceState);

        TextView toolView = view.findViewById(R.id.toolName);
        TextView toolInputView = view.findViewById(R.id.toolInput);
        TextView logView = view.findViewById(R.id.logDetails);
        Button closeButton = view.findViewById(R.id.closeButton);

        if (getArguments() != null) {
            String tool = getArguments().getString(ARG_TOOL, "");
            String toolInput = getArguments().getString(ARG_TOOL_INPUT, "");
            String log = getArguments().getString(ARG_LOG, "");

            toolView.setText("Tool: " + tool);
            toolInputView.setText(toolInput);
            logView.setText(log);
        }

        closeButton.setOnClickListener(v -> dismiss());
    }
}