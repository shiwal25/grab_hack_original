package com.example.hackon;

import com.google.gson.Gson;
import com.google.gson.JsonSyntaxException;

import okhttp3.ResponseBody;

public class Message {

    String text;//prompt
    String sender; // "user" or "agent"
    String type;
    String chain;

    public Message(String text, String sender, String chain) {
        this.text = text;
        this.sender = sender;
        this.type = type;
        this.chain = chain;
    }

    public String getText() { return text; }
    public String getSender() { return sender; }
    public String getType() { return type; }
    public String getChain() { return chain; }

    public static Message fromJson(String text) {
        try {
            return new Gson().fromJson(text, Message.class);
        } catch (JsonSyntaxException e) {
            e.printStackTrace();
            return null;
        }
    }

    public String toJson() {
        return new Gson().toJson(this);
    }
}
