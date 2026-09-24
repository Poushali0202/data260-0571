import React, { useState } from "react";

export default function CreateRecord({ user, onAdd }) {
  const [productName, setProductName] = useState("");
  const [noticeSource, setNoticeSource] = useState("");

  if (!user) {
    return <p className="notice">Login required</p>;
  }

  function handleSubmit(e) {
    e.preventDefault();
    onAdd({ productName, noticeSource });
  }

  return (
    <div className="card">
      <h2>Add a grocery notice</h2>
      <form onSubmit={handleSubmit}>
        <label>
          Product name
          <input value={productName} onChange={(e) => setProductName(e.target.value)} required />
        </label>
        <label>
          Source or manufacturer
          <input value={noticeSource} onChange={(e) => setNoticeSource(e.target.value)} required />
        </label>
        <button type="submit">Add notice</button>
      </form>
    </div>
  );
}
