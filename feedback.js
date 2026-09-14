"use strict";

const message = document.getElementById("message");
const listStatus = document.getElementById("listStatus");
const noticeTable = document.getElementById("noticeTable");
const noticeRows = document.getElementById("noticeRows");
const searchForm = document.getElementById("searchForm");
const noticeForm = document.getElementById("noticeForm");
const updateForm = document.getElementById("updateForm");
const deleteForm = document.getElementById("deleteForm");

const showListStatus = (text, kind) => {
  listStatus.textContent = text;
  listStatus.className = kind;
};

const loadNotices = async (query = "") => {
  noticeTable.hidden = true;
  noticeRows.innerHTML = "";
  showListStatus("Loading notices...", "loading");
  try {
    const response = await fetch(`/api/notices?q=${encodeURIComponent(query)}`);
    if (!response.ok) {
      throw new Error(`server responded with ${response.status}`);
    }
    const notices = await response.json();
    if (notices.length === 0) {
      showListStatus(query ? `No notices match "${query}".` : "No notices yet. Add the first one below.", "empty");
      return;
    }
    for (const notice of notices) {
      const row = noticeRows.insertRow();
      row.insertCell().textContent = notice.id;
      row.insertCell().textContent = notice.productName;
      row.insertCell().textContent = notice.noticeSource;
    }
    showListStatus("", "");
    noticeTable.hidden = false;
  } catch (error) {
    showListStatus(`Could not load notices: ${error.message}`, "error");
  }
};

// Send the request, then go back to the home view so the list reloads.
const sendAndGoHome = async (url, method, body) => {
  try {
    const response = await fetch(url, {
      method,
      headers: { "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(typeof error.detail === "string" ? error.detail : `server responded with ${response.status}`);
    }
    window.location.href = "/";
  } catch (error) {
    message.textContent = `Request failed: ${error.message}`;
  }
};

const validateNotice = () => {
  const description = document.getElementById("noticeDescription").value.trim();
  const termsAccepted = document.getElementById("terms").checked;

  if (description.length <= 25) {
    alert("The notice description must contain more than 25 characters.");
    return false;
  }
  if (!termsAccepted) {
    alert("Please agree to the terms and conditions.");
    return false;
  }
  return true;
};

searchForm.addEventListener("submit", (event) => {
  event.preventDefault();
  loadNotices(document.getElementById("searchText").value.trim());
});

noticeForm.addEventListener("submit", (event) => {
  event.preventDefault();
  if (!validateNotice() || !noticeForm.checkValidity()) {
    noticeForm.reportValidity();
    return;
  }
  const notice = Object.fromEntries(new FormData(noticeForm).entries());
  sendAndGoHome("/api/notices", "POST", notice);
});

updateForm.addEventListener("submit", (event) => {
  event.preventDefault();
  sendAndGoHome("/api/notices/1", "PUT", {
    productName: document.getElementById("updateProduct").value.trim(),
    noticeSource: document.getElementById("updateSource").value.trim(),
  });
});

deleteForm.addEventListener("submit", (event) => {
  event.preventDefault();
  sendAndGoHome("/api/notices/highest", "DELETE");
});

loadNotices();
