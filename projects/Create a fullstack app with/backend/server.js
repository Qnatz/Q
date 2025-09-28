const express = require('express');
const cors = require('cors');

const app = express();
const PORT = 5000;

// Configure CORS to allow requests from http://localhost:3000
app.use(cors({
  origin: 'http://localhost:3000'
}));

// Use express.json() to parse incoming JSON request bodies
app.use(express.json());

// Define a POST /api/todo endpoint
app.post('/api/todo', (req, res) => {
  const { todoItem } = req.body;

  if (!todoItem) {
    return res.status(400).json({ message: 'todoItem is required in the request body.' });
  }

  console.log(`Received todo item: ${todoItem}`);
  res.json({ message: `Todo item received: ${todoItem}` });
});

// Start the Express server
app.listen(PORT, () => {
  console.log(`Server listening on port ${PORT}`);
});
