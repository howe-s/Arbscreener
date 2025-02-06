const functions = require('firebase-functions');
const admin = require('firebase-admin');
const express = require('express');
const cors = require('cors');
const { DexscreenerClient } = require('dexscreener-api');

admin.initializeApp();
const app = express();
const client = new DexscreenerClient();

// Middleware
app.use(cors({ origin: true }));
app.use(express.json());

// Initialize Firestore
const db = admin.firestore();

// Main route
app.get('/', async (req, res) => {
    res.sendFile('index.html', { root: './public' });
});

// Fetch arbitrage opportunities
app.post('/landing_page_data', async (req, res) => {
    try {
        const {
            initial_investment = 10000,
            slippage = 0.0005,
            fee_percentage = 0.0003,
            search = '7vfCXTUXx5WJV5JADk17DUJ4ksgau7utNKj4b963voxs'
        } = req.body;

        // Process arbitrage data (implement your logic here)
        const arbitrageResults = await processArbitrageData(
            initial_investment,
            slippage,
            fee_percentage,
            search
        );

        res.json(arbitrageResults);
    } catch (error) {
        console.error('Error processing arbitrage data:', error);
        res.status(500).json({ error: 'Internal server error' });
    }
});

// Get logs
app.get('/get_logs', async (req, res) => {
    try {
        const logsRef = db.collection('logs').orderBy('timestamp', 'desc').limit(100);
        const snapshot = await logsRef.get();
        const logs = [];
        snapshot.forEach(doc => {
            logs.push(doc.data().message);
        });
        res.json(logs);
    } catch (error) {
        console.error('Error fetching logs:', error);
        res.status(500).json({ error: 'Error fetching logs' });
    }
});

// Helper function to process arbitrage data
async function processArbitrageData(investmentAmount, slippageRate, transactionFee, contractAddress) {
    // Implement your arbitrage processing logic here
    // This is where you'll port over the logic from your Python code
    return [];
}

// Authentication endpoints
app.post('/register', async (req, res) => {
    try {
        const { email, password } = req.body;
        const userRecord = await admin.auth().createUser({
            email,
            password,
        });
        await db.collection('users').doc(userRecord.uid).set({
            email: userRecord.email,
            createdAt: admin.firestore.FieldValue.serverTimestamp(),
        });
        res.json({ uid: userRecord.uid });
    } catch (error) {
        res.status(400).json({ error: error.message });
    }
});

// Export the Express app as a Firebase Cloud Function
exports.app = functions.https.onRequest(app); 