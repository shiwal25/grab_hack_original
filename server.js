const express = require('express');
const http = require('http');
const { Server } = require('socket.io');
const { spawn } = require('child_process');
const path = require('path');
require('dotenv').config();

// Add CORS support for Postman and other clients
const cors = require('cors');

const app = express();
app.use(cors()); // <-- Add this line
const server = http.createServer(app);
const io = new Server(server);
const PORT = 3001;

app.use(express.json());
// Add a simple test route for Postman connectivity
app.get('/ping', (req, res) => {
    res.json({ status: 'ok' });
});

// Main chat logic
io.on('connection', (socket) => {
    console.log('A user connected:', socket.id);
    let pythonProcess;
    // Start the Python agent for a new user
    socket.on('start_session', (data) => {
        console.log('Starting Python agent for user:', data.user_id);
        
        // Pass API keys and initial data to the Python process via environment variables or command-line args
        pythonProcess = spawn('python3', [path.join(__dirname, 'delivery_agent.py')], {
            env: {
                ...process.env,
                USER_ID: data.user_id,
                LOCATION: data.location,
                SITUATION: data.situation,
            }
        });

        // Listen for data from Python script (stdout)
        pythonProcess.stdout.on('data', (data) => {
            const message = data.toString().trim();
            try {
                const jsonMessage = JSON.parse(message);
                // Emit the structured message to the frontend
                socket.emit('agent_response', jsonMessage);
                console.log('Received from Python:', jsonMessage);
            } catch (e) {
                console.error('Failed to parse JSON from Python:', message);
            }
        });

        // Listen for errors from Python script (stderr)
        pythonProcess.stderr.on('data', (data) => {
            console.error('Python Error:', data.toString());
            socket.emit('error_message', 'An error occurred with the agent.');
        });
    });

    // Handle user input from the frontend
    socket.on('send_user_input', (input) => {
        if (pythonProcess) {
            // Send user's reply to the Python script's stdin
            pythonProcess.stdin.write(JSON.stringify({ input: input }) + '\n');
            console.log('Sent to Python stdin:', input);
        }
    });

    // Clean up when a user disconnects
    socket.on('disconnect', () => {
        console.log('User disconnected:', socket.id);
        if (pythonProcess) {
            pythonProcess.kill();
        }
    });
});

server.listen(PORT, () => {
    console.log(`Server is running on port ${PORT}`);
});