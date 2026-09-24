import React from "react";
import { Link, NavLink } from "react-router-dom";

export default function Navbar({ user, onLogout }) {
  return (
    <header className="navbar">
      <Link className="brand" to="/">Grocery Notices</Link>
      <nav>
        <NavLink to="/">Home</NavLink>
        {user ? (
          <>
            <NavLink to="/create">Add notice</NavLink>
            <span className="user">{user.name}</span>
            <button type="button" onClick={onLogout}>Log out</button>
          </>
        ) : (
          <NavLink to="/login">Log in</NavLink>
        )}
      </nav>
    </header>
  );
}
