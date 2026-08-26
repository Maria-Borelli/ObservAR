const data = JSON.parse(document.getElementById("stations").textContent);
const map =L.map("map").setView([-14.2,-51.9],4);
L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",{attribution:"&copy; OpenStreetMap contributors"}).addTo(map);
data.forEach(s=>L.marker([s.lat,s.lng]).addTo(map).bindPopup(`<b>${s.name}</b><br>${s.city}`));
