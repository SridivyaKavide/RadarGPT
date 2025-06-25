/**
 * Database Service for FindRadar
 * Handles all database operations for search history
 */

// This file is now deprecated. All search history is stored in PostgreSQL via backend API.

class FindRadarDbService {
  constructor() {
    this.dbPromise = this.initDatabase();
  }

  // Initialize the database
  async initDatabase() {
    return new Promise((resolve, reject) => {
      const request = indexedDB.open('FindRadarDatabase', 1);
      
      request.onerror = (event) => {
        console.error('Database error:', event.target.error);
        reject(event.target.error);
      };
      
      request.onupgradeneeded = (event) => {
        const db = event.target.result;
        
        // Create object store for search history
        if (!db.objectStoreNames.contains('searchHistory')) {
          const store = db.createObjectStore('searchHistory', { keyPath: 'id', autoIncrement: true });
          store.createIndex('query', 'query', { unique: false });
          store.createIndex('timestamp', 'timestamp', { unique: false });
        }
      };
      
      request.onsuccess = (event) => {
        resolve(event.target.result);
      };
    });
  }

  // Add a search to history
  async addSearchHistory(item) {
    try {
      const db = await this.dbPromise;
      const tx = db.transaction('searchHistory', 'readwrite');
      const store = tx.objectStore('searchHistory');
      
      // Add timestamp if not present
      if (!item.timestamp) {
        item.timestamp = new Date().toISOString();
      }
      
      const id = await store.add(item);
      return id;
    } catch (error) {
      console.error('Error adding search history:', error);
      return null;
    }
  }

  // Get all search history
  async getSearchHistory() {
    try {
      const db = await this.dbPromise;
      const tx = db.transaction('searchHistory', 'readonly');
      const store = tx.objectStore('searchHistory');
      const index = store.index('timestamp');
      
      return new Promise((resolve, reject) => {
        const request = index.openCursor(null, 'prev'); // Sort by timestamp descending
        const results = [];
        
        request.onsuccess = (event) => {
          const cursor = event.target.result;
          if (cursor) {
            results.push(cursor.value);
            cursor.continue();
          } else {
            resolve(results);
          }
        };
        
        request.onerror = (event) => {
          reject(event.target.error);
        };
      });
    } catch (error) {
      console.error('Error getting search history:', error);
      return [];
    }
  }

  // Update a search in history
  async updateSearchHistory(item) {
    try {
      const db = await this.dbPromise;
      const tx = db.transaction('searchHistory', 'readwrite');
      const store = tx.objectStore('searchHistory');
      
      await store.put(item);
      return true;
    } catch (error) {
      console.error('Error updating search history:', error);
      return false;
    }
  }

  // Delete a search from history
  async deleteSearchHistory(id) {
    try {
      const db = await this.dbPromise;
      const tx = db.transaction('searchHistory', 'readwrite');
      const store = tx.objectStore('searchHistory');
      
      await store.delete(id);
      return true;
    } catch (error) {
      console.error('Error deleting search history:', error);
      return false;
    }
  }

  // Clear all search history
  async clearSearchHistory() {
    try {
      const db = await this.dbPromise;
      const tx = db.transaction('searchHistory', 'readwrite');
      const store = tx.objectStore('searchHistory');
      
      await store.clear();
      return true;
    } catch (error) {
      console.error('Error clearing search history:', error);
      return false;
    }
  }
  
  // Limit history to most recent N entries
  async limitHistorySize(maxEntries = 50) {
    try {
      const allHistory = await this.getSearchHistory();
      
      // If we're under the limit, no action needed
      if (allHistory.length <= maxEntries) {
        return true;
      }
      
      // Sort by timestamp (newest first)
      allHistory.sort((a, b) => {
        return new Date(b.timestamp) - new Date(a.timestamp);
      });
      
      // Keep only the newest maxEntries
      const toDelete = allHistory.slice(maxEntries);
      
      const db = await this.dbPromise;
      const tx = db.transaction('searchHistory', 'readwrite');
      const store = tx.objectStore('searchHistory');
      
      // Delete older entries
      for (const item of toDelete) {
        await store.delete(item.id);
      }
      
      return true;
    } catch (error) {
      console.error('Error limiting history size:', error);
      return false;
    }
  }
}

// Create and export a singleton instance
const findRadarDb = new FindRadarDbService();

// Add a global function to view database contents from the browser console
window.viewFindRadarDatabase = function() {
  return findRadarDb.getSearchHistory().then(entries => {
    console.table(entries.map(entry => ({
      id: entry.id,
      query: entry.query,
      source: entry.source,
      timestamp: entry.timestamp
    })));
    console.log('Full database entries:', entries);
    return entries;
  });
};