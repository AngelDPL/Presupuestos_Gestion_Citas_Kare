import React, { useState, useEffect } from 'react';
import './App.css';

function App() {
	const [mensaje, setMensaje] = useState('');
	const [usuarios, setUsuarios] = useState([]);
	const [loading, setLoading] = useState(true);

	useEffect(() => {
		fetch('http://localhost:5000/api/hello')
			.then(response => response.json())
			.then(data => setMensaje(data.message))
			.catch(error => console.error('Error:', error));

		fetch('http://localhost:5000/api/usuarios')
			.then(response => response.json())
			.then(data => {
				setUsuarios(data);
				setLoading(false);
			})
			.catch(error => {
				console.error('Error:', error);
				setLoading(false);
			});
	}, []);

	return (
		<div className="App">
			<header className="App-header">
				<h1>Mi App - React + Flask</h1>
				<p>{mensaje}</p>

				<div style={{ marginTop: '2rem' }}>
					<h2>Lista de Usuarios</h2>
					{loading ? (
						<p>Cargando...</p>
					) : (
						<ul>
							{usuarios.map(usuario => (
								<li key={usuario.id}>
									<strong>{usuario.nombre}</strong> - {usuario.email}
								</li>
							))}
						</ul>
					)}
				</div>
			</header>
		</div>
	);
}

export default App;