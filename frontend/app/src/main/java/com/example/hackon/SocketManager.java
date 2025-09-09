package com.example.hackon;

import java.net.URISyntaxException;

import io.socket.client.IO;
import io.socket.client.Socket;

public class SocketManager {
    private static Socket socket;

    public static Socket getSocket() {
        if (socket == null) {
            try {
                socket = IO.socket("http://10.0.2.2:8080");
                socket.connect();
            } catch (URISyntaxException e) {
                e.printStackTrace();
            }
        }
        return socket;
    }
}
