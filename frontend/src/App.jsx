import { useEffect, useState } from "react";

export default function App() {
  const [message, setMessage] = useState("");
  const [input, setInput] = useState("");

  // Fetch current message from backend
  useEffect(() => {
    fetch("/api/message")
      .then(res => res.json())
      .then(data => setMessage(data.message));
  }, []);

  // Function to send a new message
  const updateMessage = () => {
    fetch("/api/message", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: input })
    })
      .then(res => res.json())
      .then(data => setMessage(data.message));
  };

  return (
    <div>
      <h1>Current message: {message}</h1>
      <input
        type="text"
        value={input}
        onChange={e => setInput(e.target.value)}
      />
      <button onClick={updateMessage}>Update Message</button>
    </div>
  );
}
