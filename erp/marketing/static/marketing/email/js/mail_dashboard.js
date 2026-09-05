// Mail Dashboard - Navigation, AJAX Loading, and Detail Panel

document.addEventListener('DOMContentLoaded', function() {
  // Elements
  const navItems = document.querySelectorAll('.nav-item');
  const mailViews = document.querySelectorAll('.mail-view');
  const mailDetail = document.getElementById('mailDetail');
  const closeDetailBtn = document.getElementById('closeDetail');
  const dateFilter = document.getElementById('dateFilter');

  // Navigation switching
  navItems.forEach(item => {
    item.addEventListener('click', function(e) {
      e.preventDefault();
      const view = this.dataset.view;
      
      // Update active state
      navItems.forEach(nav => nav.classList.remove('active'));
      this.classList.add('active');
      
      // Show corresponding view
      mailViews.forEach(v => {
        if (v.id === view + '-view') {
          v.style.display = 'flex';
        } else {
          v.style.display = 'none';
        }
      });
      
      // Load data for the view
      loadViewData(view);
    });
  });

  // Load inbox on page load
  loadViewData('inbox');

  // Date filter change
  if (dateFilter) {
    dateFilter.addEventListener('change', function() {
      loadViewData('sent');
    });
  }

  // Close detail panel
  if (closeDetailBtn) {
    closeDetailBtn.addEventListener('click', function() {
      mailDetail.classList.remove('open');
    });
  }

  // Refresh buttons
  document.querySelectorAll('[data-refresh]').forEach(btn => {
    btn.addEventListener('click', function() {
      const view = this.dataset.refresh;
      loadViewData(view);
    });
  });

  // Load view data function
  function loadViewData(view) {
    const viewElement = document.getElementById(view + '-view');
    if (!viewElement) return;

    const contentContainer = viewElement.querySelector('.mail-list, .templates-grid, .campaigns-list');
    if (!contentContainer) return;

    // Show loading state
    showLoadingState(contentContainer);

    let url = '';
    let params = {};

    switch(view) {
      case 'inbox':
        url = '/email/api/inbox/';
        break;
      case 'sent':
        url = '/email/api/sent/';
        params.filter = dateFilter ? dateFilter.value : 'all';
        break;
      case 'templates':
        url = '/email/api/templates/';
        break;
      case 'campaigns':
        url = '/email/api/campaigns/';
        break;
    }

    // Build query string
    const queryString = new URLSearchParams(params).toString();
    const fullUrl = queryString ? `${url}?${queryString}` : url;

    // Fetch data
    fetch(fullUrl)
      .then(response => response.json())
      .then(data => {
        if (view === 'inbox') {
          renderInbox(contentContainer, data);
        } else if (view === 'sent') {
          renderSent(contentContainer, data);
        } else if (view === 'templates') {
          renderTemplates(contentContainer, data);
        } else if (view === 'campaigns') {
          renderCampaigns(contentContainer, data);
        }
      })
      .catch(error => {
        console.error('Error loading data:', error);
        showErrorState(contentContainer);
      });
  }

  // Render functions
  function renderInbox(container, data) {
    if (!data || data.length === 0) {
      container.innerHTML = `
        <div class="empty-state">
          <i class="fas fa-inbox"></i>
          <p>No replies yet</p>
        </div>
      `;
      return;
    }

    container.innerHTML = data.map(mail => `
      <div class="mail-item ${mail.is_read ? '' : 'unread'}" data-id="${mail.id}" onclick="showMailDetail('inbox', ${mail.id})">
        <div class="mail-sender">${mail.sender}</div>
        <div class="mail-subject">${mail.subject}</div>
        <div class="mail-date">${formatDate(mail.date)}</div>
      </div>
    `).join('');
  }

  function renderSent(container, data) {
    if (!data || data.length === 0) {
      container.innerHTML = `
        <div class="empty-state">
          <i class="fas fa-paper-plane"></i>
          <p>No sent emails</p>
        </div>
      `;
      return;
    }

    container.innerHTML = data.map(mail => `
      <div class="mail-item" data-id="${mail.id}" onclick="showMailDetail('sent', ${mail.id})">
        <div class="mail-sender">${mail.recipient}</div>
        <div class="mail-subject">${mail.subject}</div>
        <div class="mail-date">${formatDate(mail.date)}</div>
      </div>
    `).join('');
  }

  function renderTemplates(container, data) {
    if (!data || data.length === 0) {
      container.innerHTML = `
        <div class="empty-state">
          <i class="fas fa-file-alt"></i>
          <p>No templates created yet</p>
          <a href="/email/template/create/" class="btn btn-primary">Create Template</a>
        </div>
      `;
      return;
    }

    container.innerHTML = data.map(template => `
      <div class="template-card" onclick="window.location.href='/email/template/${template.id}/'">
        <div class="template-header">
          <div class="template-sequence">${template.sequence_number}</div>
        </div>
        <div class="template-name">${template.name}</div>
        <div class="template-subject">${template.subject}</div>
        <div class="template-delay">
          <i class="fas fa-clock"></i> Wait ${template.delay_days} day${template.delay_days !== 1 ? 's' : ''}
        </div>
      </div>
    `).join('');
  }

  function renderCampaigns(container, data) {
    if (!data || data.length === 0) {
      container.innerHTML = `
        <div class="empty-state">
          <i class="fas fa-bullhorn"></i>
          <p>No campaigns yet</p>
          <a href="/email/campaign/create/" class="btn btn-primary">Create Campaign</a>
        </div>
      `;
      return;
    }

    container.innerHTML = data.map(campaign => `
      <div class="campaign-card" onclick="window.location.href='/email/campaign/${campaign.id}/'">
        <div class="campaign-company">${campaign.company_name}</div>
        <span class="campaign-status ${campaign.status}">${campaign.status}</span>
        <div class="campaign-progress">
          <span><i class="fas fa-envelope"></i> ${campaign.sent_count} sent</span>
          <span><i class="fas fa-reply"></i> ${campaign.reply_count} replies</span>
        </div>
      </div>
    `).join('');
  }

  // Show mail detail
  window.showMailDetail = function(type, id) {
    const url = type === 'inbox' ? `/email/api/inbox/${id}/` : `/email/api/sent/${id}/`;
    
    fetch(url)
      .then(response => response.json())
      .then(data => {
        const detailContent = document.querySelector('.detail-content');
        
        detailContent.innerHTML = `
          <div style="margin-bottom: 1.5rem;">
            <div style="font-size: 1.25rem; font-weight: 600; margin-bottom: 0.5rem;">${data.subject}</div>
            <div style="display: flex; justify-content: space-between; color: var(--text-secondary); font-size: 0.875rem; margin-bottom: 1rem;">
              <div><strong>From:</strong> ${data.sender || data.from_email}</div>
              <div>${formatFullDate(data.date)}</div>
            </div>
            ${type === 'inbox' ? `<div style="margin-bottom: 1rem; color: var(--text-secondary);"><strong>To:</strong> ${data.recipient || data.to_email}</div>` : ''}
          </div>
          <div style="padding: 1.5rem; background: var(--bg-secondary); border-radius: 8px; line-height: 1.6;">
            ${data.body || data.html_content || data.plain_text_content}
          </div>
        `;
        
        mailDetail.classList.add('open');
      })
      .catch(error => {
        console.error('Error loading mail detail:', error);
      });
  };

  // Helper functions
  function showLoadingState(container) {
    container.innerHTML = `
      <div class="loading-state">
        <i class="fas fa-spinner fa-spin"></i>
        <p>Loading...</p>
      </div>
    `;
  }

  function showErrorState(container) {
    container.innerHTML = `
      <div class="empty-state">
        <i class="fas fa-exclamation-circle"></i>
        <p>Error loading data. Please try again.</p>
      </div>
    `;
  }

  function formatDate(dateString) {
    const date = new Date(dateString);
    const now = new Date();
    const diff = now - date;
    const days = Math.floor(diff / (1000 * 60 * 60 * 24));
    
    if (days === 0) {
      return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
    } else if (days === 1) {
      return 'Yesterday';
    } else if (days < 7) {
      return date.toLocaleDateString('en-US', { weekday: 'short' });
    } else {
      return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    }
  }

  function formatFullDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { 
      year: 'numeric', 
      month: 'long', 
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  }
});
