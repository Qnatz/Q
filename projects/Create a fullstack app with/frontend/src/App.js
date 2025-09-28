import React, { useState } from 'react';
import './App.css';

function App() {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [message, setMessage] = useState(''); // This 'message' is for the form input
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [confirmationMessage, setConfirmationMessage] = useState(''); // New state for confirmation

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null); // Clear previous errors
    setConfirmationMessage(''); // Clear previous confirmation message

    try {
      const response = await fetch('http://localhost:5000/submit', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ name, email, message }),
      });

      const responseData = await response.json(); // Always parse response to get message/error

      if (!response.ok) {
        throw new Error(responseData.message || 'Something went wrong!');
      }

      console.log('Backend response:', responseData);
      // Update the confirmation message state with the message from the backend
      setConfirmationMessage(responseData.message || 'Form submitted successfully!');
      // Clear form inputs on successful submission
      setName('');
      setEmail('');
      setMessage('');
    } catch (error) {
      console.error('Submission error:', error);
      setError(error.message);
      setConfirmationMessage(''); // Ensure confirmation is cleared if an error occurs
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>Contact Us</h1>
        <form onSubmit={handleSubmit}>
          <div>
            <label htmlFor="name">Name:</label>
            <input
              type="text"
              id="name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
            />
          </div>
          <div>
            <label htmlFor="email">Email:</label>
            <input
              type="email"
              id="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>
          <div>
            <label htmlFor="message">Message:</label>
            <textarea
              id="message"
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              required
            ></textarea>
          </div>
          <button type="submit" disabled={isLoading}>
            {isLoading ? 'Submitting...' : 'Submit'}
          </button>
        </form>
        {error && <p className="error-message">{error}</p>}
        {/* Render the confirmation message prominently below the form */}
        {confirmationMessage && <p className="confirmation-message">{confirmationMessage}</p>}
      </header>
    </div>
  );
}

export default App;
