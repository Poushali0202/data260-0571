import React from "react";
import { Link } from "react-router-dom";

export default function Home({ user, notices }) {
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
        <h2>Grocery notices ({notices.length})</h2>
        <Link className="button" to="/create">Add notice</Link>
      </div>
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>Product name</th>
            <th>Source or manufacturer</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {notices.map((notice) => (
            <tr key={notice.id}>
              <td>{notice.id}</td>
              <td>{notice.productName}</td>
              <td>{notice.noticeSource}</td>
              <td>
                <Link to={`/update/${notice.id}`}>Update</Link>
                <Link className="danger" to={`/delete/${notice.id}`}>Delete</Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
