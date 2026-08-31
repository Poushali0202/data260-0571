"use strict";

const noticeForm = document.getElementById("noticeForm");
const submissionList = document.getElementById("submissionList");
const statusMessage = document.getElementById("status");

const submissionCounter = (() => {
  let count = 0;
  return () => ++count;
})();

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

  const jsonString = JSON.stringify(notice);
  console.log("Notice JSON string:", jsonString);
  const parsedNotice = JSON.parse(jsonString);

  const { productName, submitterEmail } = parsedNotice;
  console.log("Product name:", productName);
  console.log("Submitter email:", submitterEmail);

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
