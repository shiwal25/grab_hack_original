// server.js
const express = require("express");
const http = require("http");
const { Server } = require("socket.io");
const { spawn } = require("child_process");
const path = require("path");
const cors = require("cors");
require("dotenv").config();

const app = express();
app.use(cors());
app.use(express.json());

const server = http.createServer(app);
const io = new Server(server, {
  // tune as needed for your frontend
  cors: { origin: "*", methods: ["GET", "POST"] }
});

const PORT = process.env.PORT || 3001;

app.get("/ping", (req, res) => res.json({ status: "ok" }));

io.on("connection", (socket) => {
  console.log("A user connected:", socket.id);
  let pythonProcess = null;
  let stdoutBuffer = "";

  socket.on("start_session", (data) => {
    console.log("Starting Python agent for user:", data?.user_id);

    const pyExe = process.platform === "win32"
      ? path.join(__dirname, "my_env", "Scripts", "python.exe")
      : path.join(__dirname, "my_env", "bin", "python");

    const scriptPath = path.join(__dirname, "main.py");

    pythonProcess = spawn(pyExe, [scriptPath], {
      env: {
        ...process.env,
        USER_ID: data?.user_id ?? "",
        LOCATION: data?.location ?? "",
        SITUATION: data?.situation ?? "",
      },
      stdio: ["pipe", "pipe", "pipe"],
    });

    pythonProcess.on("error", (err) => {
      console.error("Failed to start Python:", err);
      socket.emit("error_message", `Failed to start Python: ${err.message}`);
    });

    pythonProcess.stdout.on("data", (chunk) => {
      stdoutBuffer += chunk.toString();
      const lines = stdoutBuffer.split("\n");
      stdoutBuffer = lines.pop() || ""; // keep partial line

      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed) continue;
        try {
          const obj = JSON.parse(trimmed);
          // forward to frontend
          socket.emit("agent_response", obj);
          // also log server-side
          console.log("PY->FE:", obj);
        } catch {
          // ignore non-JSON lines
        }
      }
    });

    pythonProcess.stderr.on("data", (data) => {
      const text = data.toString();
      console.error("Python Error:", text);
      socket.emit("error_message", text);
    });

    pythonProcess.on("close", (code, signal) => {
      console.log(`Python process ended. code=${code} signal=${signal}`);
      socket.emit("agent_response", {
        type: "session_end",
        code,
        signal
      });
    });
  });

  socket.on("send_user_input", (input) => {
    if (!pythonProcess) return;
    try {
      const userText =
        typeof input === "object" && input !== null && "input" in input
          ? input.input
          : String(input ?? "");

      const jsonLine = JSON.stringify({ input: userText }) + "\n";
      pythonProcess.stdin.write(jsonLine);
      // console.log("FE->PY:", jsonLine.trim());
    } catch (err) {
      console.error("Failed to forward user input:", err);
      socket.emit("error_message", `Failed to forward input: ${err.message}`);
    }
  });

  socket.on("end_session", () => {
    if (pythonProcess) {
      try {
        pythonProcess.stdin.end();
        pythonProcess.kill();
      } catch {}
      pythonProcess = null;
    }
  });

  socket.on("disconnect", () => {
    console.log("User disconnected:", socket.id);
    if (pythonProcess) {
      try {
        pythonProcess.stdin.end();
        pythonProcess.kill();
      } catch {}
      pythonProcess = null;
    }
  });
});

server.listen(PORT, () => {
  console.log(`Server is running on port ${PORT}`);
});
