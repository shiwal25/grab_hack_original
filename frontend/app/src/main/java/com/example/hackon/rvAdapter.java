package com.example.hackon;

import android.os.Bundle;
import android.util.Log;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.ImageButton;
import android.widget.TextView;

import androidx.annotation.NonNull;
import androidx.fragment.app.FragmentManager;
import androidx.recyclerview.widget.RecyclerView;

import java.util.ArrayList;
import java.util.List;

public class rvAdapter extends RecyclerView.Adapter<RecyclerView.ViewHolder> {

    private static final int TYPE_SENT = 0;
    private static final int TYPE_RECEIVED = 1; // Delivery side incoming
    private static final int TYPE_CHAIN = 2;    // Recipient side incoming
    private static FragmentManager fragmentManager;

    static ArrayList<Message> messages;
    boolean isUserSide; // true = recipient/user, false = delivery side

    public rvAdapter(ArrayList<Message> messages, boolean isUserSide, FragmentManager fragmentManager) {
        this.messages = messages;
        this.isUserSide = isUserSide;
        this.fragmentManager = fragmentManager;
    }

    @Override
    public int getItemViewType(int position) {
        Message msg = messages.get(position);
        if (isUserSide) {
            // Recipient side
            return "user".equalsIgnoreCase(msg.getSender()) ? TYPE_SENT : TYPE_CHAIN;
        } else {
            // Delivery side
            return "user".equalsIgnoreCase(msg.getSender()) ? TYPE_RECEIVED : TYPE_SENT;
        }
    }

    @NonNull
    @Override
    public RecyclerView.ViewHolder onCreateViewHolder(@NonNull ViewGroup parent, int viewType) {
        LayoutInflater inflater = LayoutInflater.from(parent.getContext());
        switch (viewType) {
            case TYPE_SENT:
                return new SentViewHolder(inflater.inflate(R.layout.simplemessagesend, parent, false));
            case TYPE_CHAIN:
                return new ChainViewHolder(inflater.inflate(R.layout.sendmessagetype, parent, false));
            default:
                return new ReceivedViewHolder(inflater.inflate(R.layout.simplemessagereceive, parent, false));
        }
    }

    @Override
    public void onBindViewHolder(@NonNull RecyclerView.ViewHolder holder, int position) {
        Message msg = messages.get(position);
        if (holder instanceof SentViewHolder) ((SentViewHolder) holder).bind(msg);
        else if (holder instanceof ChainViewHolder) ((ChainViewHolder) holder).bind(msg);
        else ((ReceivedViewHolder) holder).bind(msg);
    }

    @Override
    public int getItemCount() {
        return messages.size();
    }

    public void setLatestMessage(Message msg) {
        messages.add(msg);
        notifyItemInserted(messages.size() - 1);
    }

    static class SentViewHolder extends RecyclerView.ViewHolder {
        TextView textView;
        public SentViewHolder(@NonNull View itemView) {
            super(itemView);
            textView = itemView.findViewById(R.id.simpleSend);
        }
        void bind(Message msg) {
            textView.setText(msg.getText());
        }
    }

    static class ReceivedViewHolder extends RecyclerView.ViewHolder {
        TextView textView;
        public ReceivedViewHolder(@NonNull View itemView) {
            super(itemView);
            textView = itemView.findViewById(R.id.simpleReceive);
        }
        void bind(Message msg) {
            textView.setText(msg.getText());
        }
    }

    static class ChainViewHolder extends RecyclerView.ViewHolder {
        TextView textView;
        ImageButton expandBtn;

        public ChainViewHolder(@NonNull View itemView) {
            super(itemView);
            textView = itemView.findViewById(R.id.simpleReceiveType);
            expandBtn = itemView.findViewById(R.id.expandChain);

            expandBtn.setOnClickListener(view -> {
                String chainText = messages.get(getAdapterPosition()).getChain();
                if (chainText != null && !chainText.isEmpty()) {
                    ItemListDialogFragment fragment = ItemListDialogFragment.newInstance(chainText);
                    fragment.show(fragmentManager, "chain_fragment");
                }
            });
        }

        void bind(Message msg) {
            textView.setText(msg.getText());
        }
    }

    public void addMessage(Message msg) {
        messages.add(msg);
        notifyItemInserted(messages.size() - 1);
    }

    public void setMessages(List<Message> newMessages) {
        this.messages.clear();
        this.messages.addAll(newMessages);
        notifyDataSetChanged();
    }
}
