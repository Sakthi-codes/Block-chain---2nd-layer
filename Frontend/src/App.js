import React, { useState, useEffect } from "react";

function App() {
  const [sender, setSender] = useState("");
  const [recipient, setRecipient] = useState("");
  const [amount, setAmount] = useState("");
  const [chain, setChain] = useState([]);
  const [message, setMessage] = useState("");

  const API_URL = "http://127.0.0.1:5000"; // your Flask blockchain backend

  const fetchChain = async () => {
    try {
      const res = await fetch(`${API_URL}/chain`);
      const data = await res.json();
      setChain(data.chain || []);
    } catch (err) {
      console.error("Error fetching chain:", err);
    }
  };

  const submitTransaction = async () => {
    if (!sender || !recipient || !amount) {
      setMessage("Fill all fields");
      return;
    }
    try {
      const res = await fetch(`${API_URL}/transactions/new`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ sender, recipient, amount: parseFloat(amount) }),
      });
      const data = await res.json();
      setMessage(data.message || "Transaction submitted");
      setSender("");
      setRecipient("");
      setAmount("");
      fetchChain();
    } catch (err) {
      console.error("Error:", err);
      setMessage("Error submitting transaction");
    }
  };

  const mineBlock = async () => {
    try {
      const res = await fetch(`${API_URL}/mine`);
      const data = await res.json();
      setMessage(`Mined block #${data.index}`);
      fetchChain();
    } catch (err) {
      console.error("Error mining:", err);
      setMessage("Error mining block");
    }
  };

  useEffect(() => {
    fetchChain();
  }, []);

  return (
    <div style={{ maxWidth: 600, margin: "auto", padding: "2rem", fontFamily: "sans-serif" }}>
      <h1>🪙 Mini Blockchain UI</h1>

      <h2>Create Transaction</h2>
      <input
        type="text"
        placeholder="Sender"
        value={sender}
        onChange={(e) => setSender(e.target.value)}
        style={{ marginRight: "5px" }}
      />
      <input
        type="text"
        placeholder="Recipient"
        value={recipient}
        onChange={(e) => setRecipient(e.target.value)}
        style={{ marginRight: "5px" }}
      />
      <input
        type="number"
        placeholder="Amount"
        value={amount}
        onChange={(e) => setAmount(e.target.value)}
        style={{ marginRight: "5px" }}
      />
      <button onClick={submitTransaction}>Submit</button>

      <h2>Mining</h2>
      <button onClick={mineBlock}>⛏ Mine Block</button>

      {message && <p><b>{message}</b></p>}

      <h2>Blockchain</h2>
      <div style={{ maxHeight: "300px", overflowY: "auto", border: "1px solid #ddd", padding: "1rem" }}>
        {chain.map((block) => (
          <div key={block.index} style={{ marginBottom: "1rem", padding: "0.5rem", border: "1px solid #ccc" }}>
            <p><b>Block #{block.index}</b></p>
            <p>Proof: {block.proof}</p>
            <p>Prev Hash: {block.previous_hash}</p>
            <p>Txns:</p>
            <ul>
              {block.transactions.map((tx, i) => (
                <li key={i}>{tx.sender} → {tx.recipient}: {tx.amount}</li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </div>
  );
}

export default App;