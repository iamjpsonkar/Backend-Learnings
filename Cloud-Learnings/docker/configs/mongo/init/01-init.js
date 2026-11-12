// MongoDB initialization script
// Runs on first container start

db = db.getSiblingDB('labdb');

// Create collections with sample documents
db.createCollection('users');
db.users.insertMany([
    {
        _id: ObjectId(),
        username: 'alice',
        email: 'alice@example.local',
        profile: { age: 30, city: 'San Francisco' },
        tags: ['admin', 'user'],
        createdAt: new Date()
    },
    {
        _id: ObjectId(),
        username: 'bob',
        email: 'bob@example.local',
        profile: { age: 25, city: 'New York' },
        tags: ['user'],
        createdAt: new Date()
    }
]);

db.createCollection('events');
db.events.insertMany([
    {
        type: 'order.created',
        payload: { orderId: 'ORD-001', amount: 99.99, currency: 'USD' },
        timestamp: new Date(),
        processed: false
    },
    {
        type: 'user.registered',
        payload: { userId: 'USR-001', email: 'alice@example.local' },
        timestamp: new Date(),
        processed: true
    }
]);

db.createCollection('products');
db.products.insertMany([
    {
        sku: 'WGT-001',
        name: 'Widget Pro',
        price: 19.99,
        stock: 100,
        categories: ['widgets', 'bestseller'],
        metadata: { weight: '0.5kg', color: 'blue' }
    },
    {
        sku: 'GDG-001',
        name: 'Gadget Plus',
        price: 39.99,
        stock: 50,
        categories: ['gadgets'],
        metadata: { weight: '0.3kg', color: 'black' }
    }
]);

// Create indexes
db.users.createIndex({ email: 1 }, { unique: true });
db.events.createIndex({ type: 1, timestamp: -1 });
db.events.createIndex({ processed: 1 });
db.products.createIndex({ sku: 1 }, { unique: true });
db.products.createIndex({ categories: 1 });

// Create a read-only user
db.createUser({
    user: 'readonly',
    pwd: 'readonly123',
    roles: [{ role: 'read', db: 'labdb' }]
});

print('[MongoDB Init] Initialization complete.');
print('[MongoDB Init] Collections: users, events, products');
print('[MongoDB Init] Indexes created.');
