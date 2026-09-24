import React, { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { fetchNotice } from "../api.js";

export default function DeleteRecord({ user, onDelete }) {
  const { id } = useParams();
  const noticeId = Number(id);
  const [notice, setNotice] = useState(null);

  useEffect(() => {
    if (user) {
      fetchNotice(noticeId).then(setNotice).catch(() => setNotice(null));
    }
  }, [user, noticeId]);

  if (!user) {
    return <p className="notice">Login required</p>;
  }

  return (
    <div className="card">
      <h2>Delete notice {noticeId}</h2>
      {notice ? (
        <>
          <p>
            Delete <strong>{notice.productName}</strong> from {notice.noticeSource}?
          </p>
          <button type="button" className="danger" onClick={() => onDelete(noticeId)}>
            Delete notice
          </button>
        </>
      ) : (
        <p className="notice">Notice not found.</p>
      )}
    </div>
  );
}
