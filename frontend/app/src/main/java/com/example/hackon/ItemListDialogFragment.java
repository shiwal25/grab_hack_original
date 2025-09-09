package com.example.hackon;

import android.os.Bundle;

import androidx.annotation.Nullable;
import androidx.annotation.NonNull;

import com.google.android.material.bottomsheet.BottomSheetDialogFragment;

import androidx.recyclerview.widget.LinearLayoutManager;
import androidx.recyclerview.widget.RecyclerView;

import android.util.Log;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.TextView;

import com.example.hackon.databinding.FragmentItemListDialogListDialogBinding;

public class ItemListDialogFragment extends BottomSheetDialogFragment {

    private FragmentItemListDialogListDialogBinding binding;

    public static ItemListDialogFragment newInstance(String message) {
        ItemListDialogFragment fragment = new ItemListDialogFragment();
        Bundle args = new Bundle();
        args.putString("message", message);
        fragment.setArguments(args);
        return fragment;
    }
    @Nullable
    @Override
    public View onCreateView(LayoutInflater inflater, @Nullable ViewGroup container,
                             @Nullable Bundle savedInstanceState) {

        binding = FragmentItemListDialogListDialogBinding.inflate(inflater, container, false);
        return binding.getRoot();

    }
    @Override
    public void onViewCreated(@NonNull View view, @Nullable Bundle savedInstanceState) {
        TextView textView = view.findViewById(R.id.chainMessage);
        if (getArguments() != null) {
            String chainText = getArguments().getString("message");
            if (chainText != null) {
//                Log.d("TAG", "onViewCreated: dddddd"+chainText);
                textView.setText(chainText);
            }
        }
    }
    @Override
    public void onDestroyView() {
        super.onDestroyView();
        binding = null;
    }
}