const SAVED_KEY = 'radargpt_saved_queries';

/**
 * Show a dropdown to select a collection to save to,
 * and indicate which collections the query is already in.
 * @param {HTMLElement} buttonElement - The button to anchor the dropdown to.
 * @param {Function} onSelect - Callback when a collection is selected to save to.
 * @param {Object} [queryObj] - The query object (with id or query text) to enable "Added" feedback.
 */
function showCollectionDropdown(buttonElement, onSelect, queryObj = null) {
  document.querySelectorAll('.collection-dropdown-popup').forEach(el => el.remove());

  const saved = JSON.parse(localStorage.getItem(SAVED_KEY) || '{}');
  const collections = Object.keys(saved);

  // Helper: is this query already in a collection?
  function isInCollection(col) {
    if (!queryObj) return false;
    return saved[col]?.some(
      q => (queryObj.id && q.id === queryObj.id) ||
           (queryObj.query && q.query === queryObj.query)
    );
  }

  const dropdown = document.createElement('div');
  dropdown.className = 'collection-dropdown-popup';
  dropdown.style.position = 'absolute';
  const rect = buttonElement.getBoundingClientRect();
  dropdown.style.top = `${rect.bottom + 6 + window.scrollY}px`;
  dropdown.style.left = `${rect.left - 180 + window.scrollX}px`;
  dropdown.style.zIndex = 9999;
  dropdown.style.background = '#101e2b';
  dropdown.style.border = '1px solid #00fff7';
  dropdown.style.borderRadius = '10px';
  dropdown.style.boxShadow = '0 0 12px rgba(0,255,247,0.3)';
  dropdown.style.padding = '0.6rem';
  dropdown.style.minWidth = '200px';
  dropdown.style.fontFamily = 'Poppins, Montserrat, sans-serif';

  // Add custom CSS for hover effect (light color, no underline, no background)
  const style = document.createElement('style');
  style.innerHTML = `
    .collection-dropdown-popup .collection-dropdown-item {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 5px 8px;
      cursor: pointer;
      color: #b0faff;
      border-radius: 5px;
      transition: color 0.18s, font-weight 0.18s, background 0.18s;
      background: transparent !important;
      text-decoration: none;
      font-weight: 500;
      gap: 0.5em;
      font-size: 1em;
      margin-bottom: 2px;
    }
    .collection-dropdown-popup .collection-dropdown-item:hover {
      color: #fff;
      background: rgba(0,255,247,0.08);
      font-weight: 700;
      text-decoration: none;
    }
    .collection-dropdown-popup .added-label {
      color: #00ff90;
      font-size: 0.96em;
      font-weight: 700;
      margin-left: 0.5em;
      pointer-events: none;
      letter-spacing: 0.02em;
    }
  `;
  dropdown.appendChild(style);

  // ❌ Close Button
  const closeBtn = document.createElement('div');
  closeBtn.innerHTML = '&times;';
  closeBtn.style.position = 'absolute';
  closeBtn.style.top = '6px';
  closeBtn.style.right = '10px';
  closeBtn.style.cursor = 'pointer';
  closeBtn.style.fontSize = '20px';
  closeBtn.style.color = '#00fff7';
  closeBtn.title = 'Close';
  closeBtn.onclick = () => dropdown.remove();
  dropdown.appendChild(closeBtn);

  const title = document.createElement('div');
  title.innerText = '📁 Choose a collection:';
  title.style.marginBottom = '0.4rem';
  title.style.color = '#00fff7';
  title.style.fontWeight = '600';
  dropdown.appendChild(title);

  collections.forEach(col => {
    const item = document.createElement('div');
    item.className = 'collection-dropdown-item';
    // Left: collection name
    const nameSpan = document.createElement('span');
    nameSpan.textContent = col;
    item.appendChild(nameSpan);

    if (isInCollection(col)) {
      // Already added: show "Added" and disable click
      const added = document.createElement('span');
      added.className = 'added-label';
      added.textContent = 'Added';
      item.appendChild(added);

      item.style.opacity = 0.7;
      item.style.pointerEvents = 'none';
      item.onclick = null;
    } else {
      // Not added: allow adding
      item.onclick = () => {
        dropdown.remove();
        onSelect(col);
      };
    }
    dropdown.appendChild(item);
  });

  const separator = document.createElement('hr');
  separator.style.margin = '0.5rem 0';
  separator.style.border = 'none';
  separator.style.borderTop = '1px solid #00fff7';
  dropdown.appendChild(separator);

  const input = document.createElement('input');
  input.placeholder = 'New collection name';
  input.style.width = '90%';
  input.style.padding = '5px 8px';
  input.style.borderRadius = '5px';
  input.style.border = '1px solid #00fff7';
  input.style.background = '#000';
  input.style.color = '#fff';
  input.style.marginBottom = '0.4rem';
  dropdown.appendChild(input);

  const createBtn = document.createElement('button');
  createBtn.innerText = '➕ Create & Save';
  createBtn.style.width = '100%';
  createBtn.style.padding = '7px';
  createBtn.style.background = '#00fff7';
  createBtn.style.color = '#001f2f';
  createBtn.style.border = 'none';
  createBtn.style.borderRadius = '5px';
  createBtn.style.cursor = 'pointer';
  createBtn.style.fontWeight = '600';
  createBtn.onclick = () => {
    const val = input.value.trim();
    if (val) {
      dropdown.remove();
      onSelect(val);
    }
  };
  dropdown.appendChild(createBtn);

  document.body.appendChild(dropdown);

  // Optional: Remove the dropdown if user clicks outside
  setTimeout(() => {
    function outsideClick(e) {
      if (!dropdown.contains(e.target) && e.target !== buttonElement) {
        dropdown.remove();
        document.removeEventListener('mousedown', outsideClick);
      }
    }
    document.addEventListener('mousedown', outsideClick);
  }, 0);
}

/**
 * Save a query to a collection, and show "Added" feedback in dropdown.
 * @param {string} query
 * @param {string} summaryHTML
 * @param {HTMLElement} buttonElement
 * @param {string} sourcesHtml
 */
function saveToSavedCollection(query, summaryHTML, buttonElement = null, sourcesHtml = '') {
  // Pass the query object for "already added" feedback
  const queryObj = {
    id: buttonElement?.dataset?.saveId || null,
    query
  };
  showCollectionDropdown(buttonElement, collection => {
    let saved = JSON.parse(localStorage.getItem(SAVED_KEY) || '{}');
    if (!saved[collection]) saved[collection] = [];

    saved[collection].unshift({
      id: queryObj.id || 'saved_' + Date.now(),
      query,
      html: summaryHTML,
      sourcesHtml
    });

    localStorage.setItem(SAVED_KEY, JSON.stringify(saved));

    if (buttonElement) {
      buttonElement.innerHTML = '✅ Saved';
      buttonElement.disabled = true;
      buttonElement.style.color = '#00ff90';
      setTimeout(() => {
        buttonElement.innerHTML = '<span style="font-size: 1.2em;">🔖</span><span style="font-size: 0.95em;">Save to Stacks</span>';
        buttonElement.disabled = false;
        buttonElement.style.color = '#00fff7';
      }, 3000);
    }
  }, queryObj);
}

document.addEventListener('DOMContentLoaded', function () {
  if (document.getElementById('saved-results')) {
    renderSaved();
  }
});
