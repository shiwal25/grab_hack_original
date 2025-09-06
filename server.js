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

    socket.on('start_session', (data) => {
        console.log('Starting Python agent for user:', data.user_id);

        const pythonExecutable = path.join(__dirname, 'venv', 'Scripts', 'python.exe');
        pythonProcess = spawn(pythonExecutable, [path.join(__dirname, 'main.py')], {
            env: {
                ...process.env,
                USER_ID: data.user_id,
                LOCATION: data.location,
                SITUATION: data.situation,
            }
        });

        // Buffer stdout and emit each valid JSON line to the frontend
        let buffer = '';
        pythonProcess.stdout.on('data', (data) => {
            buffer += data.toString();
            const lines = buffer.split('\n');
            buffer = lines.pop(); // keep incomplete line in buffer
            for (const line of lines) {
                try {
                    const jsonMessage = JSON.parse(line.trim());
                    socket.emit('agent_response', jsonMessage);
                    console.log('Received from Python:', jsonMessage);
                } catch (e) {
                    // Not JSON, ignore
                }
            }
        });

        pythonProcess.stderr.on('data', (data) => {
            socket.emit('error_message', data.toString());
            console.error('Python Error:', data.toString());
        });
    });

socket.on('send_user_input', (input) => {
    if (pythonProcess) {
        try {
            // Check if the input is a JSON object and has an 'input' key.
            // If it's a string, we assume it's the raw user input.
            const userText = typeof input === 'object' && input !== null && 'input' in input
                ? input.input
                : input;

            // Python expects a JSON string, so we must stringify it.
            // The JSON.stringify() method is what makes it work.
            const jsonInput = JSON.stringify({ input: userText });
            
            // Write the JSON string to Python's stdin, followed by a newline.
            pythonProcess.stdin.write(jsonInput + '\n');
            
            console.log('Sent to Python stdin:', jsonInput);
        } catch (error) {
            console.error('Failed to process user input:', error);
        }
    }
});

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