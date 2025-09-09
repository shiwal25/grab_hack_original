package com.example.hackon;

import android.os.Handler;
import android.os.Looper;
import android.util.Log;

import org.json.JSONObject;

import java.util.HashMap;
import java.util.Map;

import io.socket.client.Socket;

/**
 * A central event dispatcher for socket events.
 * - Only attaches socket listener once.
 * - Broadcasts events to all registered activity listeners.
 */
public class SocketEventDispatcher {

    public interface SocketEventListener {
        void onAgentResponse(Object[] args);
    }

    private static final Map<String, SocketEventListener> listeners = new HashMap<>();
    private static boolean initialized = false;
    private static final Handler mainHandler = new Handler(Looper.getMainLooper());

    public static void init(Socket socket) {
        if (initialized) return;
        initialized = true;

        socket.on("agent_response", args -> {
            // Log raw message
            if (args.length > 0 && args[0] instanceof JSONObject) {
                Log.d("SocketEventDispatcher", "agent_response: " + args[0].toString());
            }

            // Dispatch to all listeners on main thread
            mainHandler.post(() -> {
                for (SocketEventListener listener : listeners.values()) {
                    listener.onAgentResponse(args);
                }
            });
        });
    }

    public static void registerListener(String key, SocketEventListener listener) {
        listeners.put(key, listener);
    }

    public static void unregisterListener(String key) {
        listeners.remove(key);
    }
}
