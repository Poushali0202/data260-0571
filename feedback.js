"use strict";

const noticeForm = document.getElementById("noticeForm");
const submissionList = document.getElementById("submissionList");
const statusMessage = document.getElementById("status");

// Closure: the private count survives between successful submissions.
const submissionCounter = (() => {
  let count = 0;
  return () => ++count;
})();

// Arrow-function validation required by the assignment.
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

noticeForm.addEventListener("submit", (event) => {
  event.preventDefault();
  if (!validateNotice() || !noticeForm.checkValidity()) {
    noticeForm.reportValidity();
    return;
  }

  const formData = new FormData(noticeForm);
  const notice = Object.fromEntries(formData.entries());
  notice.terms = document.getElementById("terms").checked;

  // JSON conversion, parsing, and console output.
  const jsonString = JSON.stringify(notice);
  console.log("Notice JSON string:", jsonString);
  const parsedNotice = JSON.parse(jsonString);

  // Object destructuring extracts the primary field and submitter email.
  const { productName, submitterEmail } = parsedNotice;
  console.log("Product name:", productName);
  console.log("Submitter email:", submitterEmail);

  // Spread creates a new object with the required timestamp field.
  const updatedNotice = {
    ...parsedNotice,
    submissionDate: new Date().toISOString()
  };
  console.log("Updated notice:", updatedNotice);

  const submissionCount = submissionCounter();
  console.log("Successful submission count:", submissionCount);
  addNoticeToPage(updatedNotice, submissionCount);
  statusMessage.textContent = `Notice ${submissionCount} submitted successfully.`;
  noticeForm.reset();
  document.getElementById("productName").focus();
});

const addNoticeToPage = (notice, submissionCount) => {
  const item = document.createElement("li");
  item.textContent =
    `${notice.productName} (${notice.noticeCategory}) — ${notice.noticeDescription} ` +
    `[submission ${submissionCount}]`;
  submissionList.appendChild(item);
};
