function UserList({ users }) {
  const active = users.filter(u => u.active).map(u => u.name);
  return <ul>{active.map(name => <li key={name}>{name}</li>)}</ul>;
}
