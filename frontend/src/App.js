import React, { useState, useEffect } from 'react';
import './App.css';

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [user, setUser] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [emails, setEmails] = useState([]);
  const [loading, setLoading] = useState(false);
  const [selectedEmailIdx, setSelectedEmailIdx] = useState(null);
  const [replyText, setReplyText] = useState('');

 const BACKEND_URL = process.env.REACT_APP_API_URL



  useEffect(() => {
    const token = new URLSearchParams(window.location.search).get('token') ||
                   localStorage.getItem('authToken');

    if (token) {
      localStorage.setItem('authToken', token);
      setIsAuthenticated(true);
      fetchUserProfile(token);
      addMessage('system', '👋 Welcome! Commands: "show emails", "summarize [#]", "reply [#]", "send", "delete [#]"');
    }
  }, []);

  const fetchUserProfile = async (token) => {
    try {
      const res = await fetch(`${BACKEND_URL}/me`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const data = await res.json();
      setUser(data);
    } catch (err) {
      console.error('Profile fetch error:', err);
    }
  };

  const addMessage = (role, text) => {
    setMessages(prev => [...prev, { role, text, id: Date.now() }]);
  };

  const handleLogin = () => {
    window.location.href = `${BACKEND_URL}/auth/google/login`;
  };

  const handleLogout = () => {
    localStorage.removeItem('authToken');
    setIsAuthenticated(false);
    setUser(null);
    setMessages([]);
    setEmails([]);
  };

  const handleSendMessage = async () => {
    if (!input.trim()) return;

    const userMsg = input.trim().toLowerCase();
    addMessage('user', input);
    setInput('');
    setLoading(true);

    try {
      const token = localStorage.getItem('authToken');
      const headers = { 'Authorization': `Bearer ${token}` };

      // SHOW EMAILS
      if (userMsg.includes('show') && userMsg.includes('email')) {
        addMessage('system', '📧 Fetching your emails...');
        const res = await fetch(`${BACKEND_URL}/read-emails`, { headers });
        const data = await res.json();
        setEmails(data.emails || []);
        addMessage('system', `✅ Found ${data.emails?.length || 0} emails`);

        data.emails?.forEach((email, idx) => {
          addMessage('system', `[${idx + 1}] From: ${email.sender}\n    Subject: ${email.subject}`);
        });
      }

      // SUMMARIZE EMAIL
      else if (userMsg.includes('summarize')) {
        const match = userMsg.match(/\d+/);
        const idx = match ? parseInt(match[0]) - 1 : 0;

        if (!emails[idx]) {
          addMessage('system', '❌ Email not found. Try "show emails" first.');
        } else {
          addMessage('system', '🤖 Summarizing...');
          const res = await fetch(`${BACKEND_URL}/summarize-email?email_id=${emails[idx].id}`, {
            method: 'POST',
            headers
          });
          const data = await res.json();
          addMessage('system', `📝 Summary:\n${data.summary}`);
          setSelectedEmailIdx(idx);
        }
      }

      // GENERATE REPLY
      else if (userMsg.includes('reply')) {
        const match = userMsg.match(/\d+/);
        const idx = match ? parseInt(match[0]) - 1 : selectedEmailIdx;

        if (idx === null || !emails[idx]) {
          addMessage('system', '❌ Select email first. Try "show emails" then "reply [#]"');
        } else {
          addMessage('system', '✍️ Generating reply...');
          const res = await fetch(`${BACKEND_URL}/generate-reply?email_id=${emails[idx].id}`, {
            method: 'POST',
            headers
          });
          const data = await res.json();
          setReplyText(data.reply);
          addMessage('system', `📧 Reply ready:\n${data.reply}\n\nType "send" to send it.`);
          setSelectedEmailIdx(idx);
        }
      }

      // SEND EMAIL
       else if (userMsg.includes('send')) {
              if (!replyText || selectedEmailIdx === null) {
                addMessage('system', '❌ No reply to send. Try "reply [#]" first.');
              } else {
                // Extract email from sender string (handles "Name <email@domain.com>" format)
                const senderStr = emails[selectedEmailIdx].sender;
                const emailMatch = senderStr.match(/([a-zA-Z0-9._-]+@[a-zA-Z0-9._-]+\.[a-zA-Z0-9_-]+)/);
                const toEmail = emailMatch ? emailMatch[1] : senderStr;
                const subject = `Re: ${emails[selectedEmailIdx].subject}`;

                addMessage('system', '📤 Sending email...');
                const res = await fetch(`${BACKEND_URL}/send-email`, {
                  method: 'POST',
                  headers: {
                    'Authorization': `Bearer ${localStorage.getItem('authToken')}`,
                    'Content-Type': 'application/json'
                  },
                  body: JSON.stringify({
                    to: toEmail,
                    subject: subject,
                    body: replyText
                  })
                });

                const data = await res.json();

                if (data.success) {
                  addMessage('system', '✅ Email sent successfully!');
                  setReplyText('');
                  setSelectedEmailIdx(null);
                } else {
                  addMessage('system', `❌ Send failed: ${data.error || data.message || 'Unknown error'}`);
                }
              }
            }

      // DELETE EMAIL
      else if (userMsg.includes('delete')) {
        const match = userMsg.match(/\d+/);
        const idx = match ? parseInt(match[0]) - 1 : selectedEmailIdx;

        if (!emails[idx]) {
          addMessage('system', '❌ Email not found.');
        } else {
          addMessage('system', '🗑️ Deleting email...');
          const res = await fetch(`${BACKEND_URL}/delete-email`, {
            method: 'POST',
            headers: { ...headers, 'Content-Type': 'application/json' },
            body: JSON.stringify({ email_id: emails[idx].id })
          });
          const data = await res.json();

          if (data.success) {
            addMessage('system', '✅ Email deleted!');
            setEmails(emails.filter((_, i) => i !== idx));
          } else {
            addMessage('system', `❌ Delete failed: ${data.error}`);
          }
        }
      }

      else {
        addMessage('system', '❓ Commands: "show emails", "summarize [#]", "reply [#]", "send", "delete [#]"');
      }
    } catch (err) {
      addMessage('system', `❌ Error: ${err.message}`);
    }
    setLoading(false);
  };

  if (!isAuthenticated) {
    return (
      <div className="login-container">
        <div className="login-card">
          <h1>📧 Gmail AI Assistant</h1>
          <p>AI-powered email management</p>
          <button className="btn-primary" onClick={handleLogin}>
            🔐 Login with Google
          </button>
          <p className="footer-text">Reads, summarizes, and replies to emails with AI</p>
        </div>
      </div>
    );
  }

  return (
    <div className="dashboard-container">
      <div className="header">
        <h1>📧 Gmail AI Assistant</h1>
        <div className="header-right">
          {user && <span className="user-email">{user.email}</span>}
          <button className="btn-logout" onClick={handleLogout}>Logout</button>
        </div>
      </div>

      <div className="main-content">
        <div className="chat-area">
          {messages.map(msg => (
            <div key={msg.id} className={`message msg-${msg.role}`}>
              {msg.text.split('\n').map((line, i) => <div key={i}>{line}</div>)}
            </div>
          ))}
        </div>

        <div className="input-area">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
            placeholder="show emails / summarize [#] / reply [#] / send / delete [#]"
            disabled={loading}
          />
          <button onClick={handleSendMessage} disabled={loading} className="btn-primary">
            {loading ? '⏳' : '→'}
          </button>
        </div>
      </div>
    </div>
  );
}

export default App;
