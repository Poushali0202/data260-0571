import React, { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { fetchNotice } from "../api.js";

export default function UpdateRecord({ user, onUpdate }) {
  const { id } = useParams();
  const noticeId = Number(id);
  const [productName, setProductName] = useState("");
  const [noticeSource, setNoticeSource] = useState("");

  useEffect(() => {
    if (user) {
      fetchNotice(noticeId).then((notice) => {
        setProductName(notice.productName);
        setNoticeSource(notice.noticeSource);
      });
    }
  }, [user, noticeId]);

  if (!user) {
    return <p className="notice">Login required</p>;
  }

  function handleSubmit(e) {
    e.preventDefault();
    onUpdate(noticeId, { productName, noticeSource });
  }

  return (
    <div className="card">
      <h2>Update notice {noticeId}</h2>
      <form onSubmit={handleSubmit}>
        <label>
          Product name
          <input value={productName} onChange={(e) => setProductName(e.target.value)} required />
        </label>
        <label>
          Source or manufacturer
          <input value={noticeSource} onChange={(e) => setNoticeSource(e.target.value)} required />
        </label>
        <button type="submit">Update notice</button>
      </form>
    </div>
  );
}
