/**
 * Direct implementation of Save to Stacks functionality
 * This avoids quota issues by limiting the size of saved content
 */

function saveToStacks(query, summaryHTML, buttonElement, sourcesHtml = '', collectionName = 'Default Collection') {
  try {
    // Get current saved items
    let saved = {};
    try {
      const savedStr = localStorage.getItem('radargpt_saved_queries');
      if (savedStr) saved = JSON.parse(savedStr);
    } catch (e) {
      console.warn('Error parsing saved queries, starting fresh');
    }
    
    // Initialize collection if needed
    if (!saved[collectionName]) saved[collectionName] = [];
    
    // Limit collection size to avoid quota issues
    if (saved[collectionName].length > 20) {
      saved[collectionName] = saved[collectionName].slice(0, 20);
    }
    
    // Add new item with size limits
    saved[collectionName].unshift({
      id: 'saved_' + Date.now(),
      query: query,
      html: summaryHTML.substring(0, 10000), // Limit size
      sourcesHtml: sourcesHtml ? sourcesHtml.substring(0, 5000) : '' // Limit size
    });
    
    // Save back to localStorage
    localStorage.setItem('radargpt_saved_queries', JSON.stringify(saved));
    
    // Show confirmation
    const originalHTML = buttonElement.innerHTML;
    buttonElement.innerHTML = '<span style="font-size: 1.2em;">✅</span> <span style="font-size: 0.95em;">Saved</span>';
    buttonElement.disabled = true;
    buttonElement.style.color = '#00ff90';
    
    setTimeout(() => {
      buttonElement.innerHTML = originalHTML;
      buttonElement.disabled = false;
      buttonElement.style.color = '';
    }, 3000);
    
    return true;
  } catch (e) {
    console.error('Error saving to stacks:', e);
    alert('Could not save: Storage quota exceeded. Try clearing some saved items first.');
    return false;
  }
}

// Make function globally available
window.saveToStacks = saveToStacks;