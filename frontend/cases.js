// Make testCases accessible globally in this file
let testCases = [];

document.addEventListener('DOMContentLoaded', function() {
  // Get the test cases from localStorage
  const qaResults = localStorage.getItem('qa_results');
  const testCasesList = document.getElementById('test-cases-list');
  const emptyState = document.getElementById('empty-state');
  const searchInput = document.getElementById('search-cases');
  const filterPills = document.querySelectorAll('.filter-pill');

  console.log('Loaded qa_results from localStorage:', qaResults);
  // Clear existing test cases before loading new ones
  testCases = []; 
  
if (qaResults) {
    try {
      const data = JSON.parse(qaResults);
      
      // --- FIX STARTS HERE ---
      // Check for the nested 'output' object before looking for 'test_cases'
      if (data && data.output && Array.isArray(data.output.test_cases) && data.output.test_cases.length > 0) {
        // Assign from the correct path: data.output.test_cases
        testCases = data.output.test_cases;
      }
      // --- FIX ENDS HERE ---

    } catch (error) {
      console.error('Error parsing qa_results from localStorage:', error);
    }
  }
      
      // Function to render test cases
      function renderTestCases(cases) {
        testCasesList.innerHTML = '';
        
        if (!cases || cases.length === 0) {
          testCasesList.classList.add('d-none');
          emptyState.classList.remove('d-none');
          return;
        }
        
        testCasesList.classList.remove('d-none');
        emptyState.classList.add('d-none');
        
        cases.forEach(testCase => {
          // Default type and priority if they are missing
          const type = testCase.type || 'unknown';
          const priority = testCase.priority || 'medium';

          const typeClass = `type-${type.toLowerCase()}`;
          const priorityClass = `priority-${priority.toLowerCase()}`;
          
          const testCaseElement = document.createElement('div');
          testCaseElement.className = 'test-case-container';
          testCaseElement.innerHTML = `
            <div class="test-case-header">
              <h3 class="test-case-title">${testCase.title || `Test Case #${testCase.id}`}</h3>
              <div>
                <span class="test-case-type ${typeClass} me-2">${type.charAt(0).toUpperCase() + type.slice(1)}</span>
                <span class="priority-badge ${priorityClass}">${priority}</span>
              </div>
            </div>
            <div class="test-case-content">
              ${testCase.description ? `
                <div class="test-case-section">
                  <h5>Description</h5>
                  <p>${testCase.description}</p>
                </div>
              ` : ''}
              ${testCase.preconditions ? `
                <div class="test-case-section">
                  <h5>Preconditions</h5>
                  <p>${testCase.preconditions}</p>
                </div>
              ` : ''}
              ${testCase.testSteps && testCase.testSteps.length > 0 ? `
                <div class="test-case-section">
                  <h5>Test Steps</h5>
                  <ol>
                    ${testCase.testSteps.map(step => `<li>${step}</li>`).join('')}
                  </ol>
                </div>
              ` : ''}
              ${testCase.expectedResult ? `
                <div class="test-case-section">
                  <h5>Expected Result</h5>
                  <p>${testCase.expectedResult}</p>
                </div>
              ` : ''}
            </div>
          `;
          
          testCasesList.appendChild(testCaseElement);
        });
      }
      
      // Initial render
      renderTestCases(testCases);
      
      // Search functionality
      searchInput.addEventListener('input', function() {
        const searchTerm = this.value.toLowerCase();
        
        // Use the active filter to narrow down the search
        const activeFilter = document.querySelector('.filter-pill.active').getAttribute('data-filter');
        let casesToSearch = testCases;

        if (activeFilter !== 'all') {
            casesToSearch = testCases.filter(tc => tc.type.toLowerCase() === activeFilter);
        }
        
        if (!searchTerm) {
          renderTestCases(casesToSearch);
          return;
        }
        
        const filteredCases = casesToSearch.filter(testCase => {
          const title = (testCase.title || '').toLowerCase();
          const description = (testCase.description || '').toLowerCase();
          const preconditions = (testCase.preconditions || '').toLowerCase();
          const expectedResult = (testCase.expectedResult || '').toLowerCase();
          const type = (testCase.type || '').toLowerCase();
          const priority = (testCase.priority || '').toLowerCase();
          
          // Also search in test steps if they exist
          const stepsText = testCase.testSteps ? 
            testCase.testSteps.join(' ').toLowerCase() : '';
          
          return title.includes(searchTerm) || 
                 description.includes(searchTerm) || 
                 preconditions.includes(searchTerm) || 
                 expectedResult.includes(searchTerm) || 
                 type.includes(searchTerm) || 
                 priority.includes(searchTerm) ||
                 stepsText.includes(searchTerm);
        });
        
        renderTestCases(filteredCases);
      });
      
      // Filter functionality
      filterPills.forEach(pill => {
        pill.addEventListener('click', function() {
          // Update active state
          filterPills.forEach(p => p.classList.remove('active'));
          this.classList.add('active');
          
          const filterValue = this.getAttribute('data-filter');
          
          // Trigger a search input event to re-filter based on current search term
          searchInput.dispatchEvent(new Event('input'));
        });
      });
    });

    // Export functionality
    // Robust export event binding (delegation)
    document.addEventListener('click', function(e) {
      const exportBtn = e.target.closest('.btn-export');
      if (!exportBtn) return;
      // Export test cases as CSV
      if (!testCases || testCases.length === 0) {
        alert('No test cases to export.');
        return;
      }
      // Prepare CSV header
      const headers = ['ID','Title','Type','Description','Preconditions','Test Steps','Expected Result','Priority'];
      const csvRows = [headers.join(',')];
      testCases.forEach(tc => {
        const steps = tc.testSteps ? tc.testSteps.map(s => s.replace(/"/g, '""')).join(' | ') : '';
        const row = [
          tc.id || '',
          '"' + (tc.title || '').replace(/"/g, '""') + '"',
          tc.type || '',
          '"' + (tc.description || '').replace(/"/g, '""') + '"',
          '"' + (tc.preconditions || '').replace(/"/g, '""') + '"',
          '"' + steps + '"',
          '"' + (tc.expectedResult || '').replace(/"/g, '""') + '"',
          tc.priority || ''
        ];
        csvRows.push(row.join(','));
      });
      const csvContent = csvRows.join('\r\n');
      const blob = new Blob([csvContent], { type: 'text/csv' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'test_cases_export.csv';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      setTimeout(() => URL.revokeObjectURL(url), 100);
    });