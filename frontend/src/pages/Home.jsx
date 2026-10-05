import React from "react";
import { Link } from "react-router-dom";
import { useDispatch, useSelector } from "react-redux";
import { deleteNotice } from "../features/notices/noticesSlice.js";

export default function Home({ user }) {
  const dispatch = useDispatch();
  const { items, status, error } = useSelector((state) => state.notices);

  if (!user) {
    return (
      <p className="notice">
        Login required. <Link to="/login">Log in</Link> to see the grocery notices.
      </p>
    );
  }

  return (
    <div className="card">
      <div className="card-header">
        <h2>Grocery notices ({items.length})</h2>
        <Link className="button" to="/create">Add notice</Link>
      </div>
      {status === "loading" && <p>Loading...</p>}
      {error && <p className="error">{error}</p>}
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>Code</th>
            <th>Product name</th>
            <th>Source</th>
            <th>Units</th>
            <th>Supplier</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {items.map((notice) => (
            <tr key={notice.id}>
              <td>{notice.id}</td>
              <td>{notice.noticeCode}</td>
              <td>{notice.productName}</td>
              <td>{notice.noticeSource}</td>
              <td>{notice.affectedUnits}</td>
              <td>{notice.supplierId}</td>
              <td>
                <Link to={`/update/${notice.id}`}>Update</Link>
                <button type="button" className="danger" onClick={() => dispatch(deleteNotice(notice.id))}>
                  Delete
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
