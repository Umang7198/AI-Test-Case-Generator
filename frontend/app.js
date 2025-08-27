// Custom JS from input.html
// Render hCaptcha only after the library is loaded and config is available
window.hcaptchaOnLoad = function() {
  var siteKey = window.hcaptchaConfig && window.hcaptchaConfig.siteKey;
  if (!siteKey) {
    console.error('hCaptcha sitekey missing!');
    return;
  }
  window.hcaptcha.render('hcaptcha-widget', { sitekey: siteKey });
};

document.addEventListener('DOMContentLoaded', function() {
  var qaForm = document.getElementById('qaForm');
  if (qaForm) {
    qaForm.addEventListener('submit', async function(event) {
      event.preventDefault();
      var captchaResponse = window.hcaptcha.getResponse();
      var errorDiv = document.getElementById('captcha-error');
      var statusDiv = document.getElementById('status');

      if (!captchaResponse) {
        errorDiv.classList.remove('d-none');
        statusDiv.innerHTML = '';
        return;
      } else {
        errorDiv.classList.add('d-none');
      }

      statusDiv.innerHTML = '<div class="alert alert-info"><i class="fas fa-spinner fa-spin me-2"></i>Generating test cases...</div>';

      var inputText = document.getElementById('input_text').value.trim();
      var files = document.getElementById('files').files;
      var inputErrorDiv = document.getElementById('input-error');

      // Require at least one: text or file
      if (!inputText && (!files || files.length === 0)) {
        inputErrorDiv.classList.remove('d-none');
        statusDiv.innerHTML = '';
        return;
      } else {
        inputErrorDiv.classList.add('d-none');
      }

      var formData = new FormData();
      formData.append('input_text', inputText);
      formData.append('h-captcha-response', captchaResponse);

      for (var i = 0; i < files.length; i++) {
        formData.append('files', files[i]);
      }

      try {
        const res = await fetch('http://127.0.0.1:8000/process', {
          method: 'POST',
          body: formData
        });

        const data = await res.json();

        if (data.error) {
          statusDiv.innerHTML = `<div class="alert alert-danger"><i class="fas fa-exclamation-circle me-2"></i>${data.error}</div>`;
        } else {
          localStorage.setItem('qa_results', JSON.stringify(data));
          console.log('Stored qa_results in localStorage:', JSON.stringify(data));
          window.location.href = 'cases.html';
        }
      } catch (err) {
        statusDiv.innerHTML = `<div class="alert alert-danger"><i class="fas fa-exclamation-circle me-2"></i>Error: ${err.message}</div>`;
      }
    });
  }
});
// Backend URL
const API_URL = "http://127.0.0.1:8000";  // FastAPI backend

// Handle Input Form Submit
document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("input-form");
  if (form) {
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const status = document.getElementById("status");
      status.innerHTML = "⏳ Generating...";

      const requirements = document.getElementById("requirements").value;
      const files = document.getElementById("documents").files;
      const captchaToken = document.querySelector("[name='h-captcha-response']").value;

      if (!captchaToken) {
        status.innerHTML = "<span class='text-danger'>❌ Please complete CAPTCHA</span>";
        return;
      }

      let formData = new FormData();
      formData.append("requirements", requirements);
      formData.append("captcha_token", captchaToken);
      for (let i = 0; i < files.length; i++) {
        formData.append("files", files[i]);
      }

      const res = await fetch(`${API_URL}/generate`, {
        method: "POST",
        body: formData
      });

      const data = await res.json();
      if (data.error) {
        status.innerHTML = `<span class="text-danger">❌ ${data.error}</span>`;
      } else {
        status.innerHTML = "<span class='text-success'>✅ Success! View results in Test Cases / Test Data.</span>";
        localStorage.setItem("qa_results", JSON.stringify(data));
      }
    });
  }

  // Populate Test Cases Page
  if (document.getElementById("test-cases-list")) {
    const results = JSON.parse(localStorage.getItem("qa_results") || "{}");
    const listDiv = document.getElementById("test-cases-list");
    // Support both old and new backend response structure
    const reviewed = results.reviewed_test_cases || (results.output && results.output.reviewed_test_cases);
    if (reviewed) {
      if (reviewed.includes('no requirement provided') || reviewed.includes('no test cases to review')) {
        listDiv.innerHTML = `<div class=\"alert alert-warning\">No requirement was provided, so no test cases were generated.<br>Please provide a requirement to generate test cases.</div><div class=\"p-3 bg-light border\">${window.marked.parse(reviewed)}</div>`;
      } else {
        listDiv.innerHTML = `<div class=\"p-3 bg-light border\">${window.marked.parse(reviewed)}</div>`;
      }
    } else {
      listDiv.innerHTML = "<p class='text-muted'>No test cases yet.</p>";
    }
  }

  // Populate Test Data Page
  if (document.getElementById("data-rows")) {
    const results = JSON.parse(localStorage.getItem("qa_results") || "{}");
    const dataSection = document.getElementById("data-rows").parentElement.parentElement;
    const testData = results.test_data_table || (results.output && results.output.test_data_table);
    if (testData) {
      if (testData.includes('|  |  |  |  |') || testData.includes('the table is empty')) {
        dataSection.innerHTML = `<div class=\"alert alert-warning\">No test data available. Please provide a requirement and generate test cases first.</div>` + window.marked.parse(testData);
      } else {
        const tableHTML = window.marked.parse(testData);
        dataSection.innerHTML = tableHTML;
      }
    } else {
      document.getElementById("data-rows").innerHTML = "<tr><td colspan='3' class='text-muted'>No test data yet.</td></tr>";
    }
  }
});
