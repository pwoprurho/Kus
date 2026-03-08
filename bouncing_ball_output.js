```javascript
// 1. Physical Constants
const gravity = new CANNON.Vec3(0, -9.82, 0);
const world = new CANNON.World({ gravity: gravity });

const defaultPhysicMaterial = new CANNON.Material('default');
const ballPhysicMaterial = new CANNON.Material('ball');
const groundPhysicMaterial = new CANNON.Material('ground');

// Physics Protocol: Contact Materials
const ballGroundContact = new CANNON.ContactMaterial(ballPhysicMaterial, groundPhysicMaterial, {
    friction: 0.3,  // Specified friction
    restitution: 0.7 // Specified ball restitution
});
world.addContactMaterial(ballGroundContact);

// Universal Standards: Materials
const defaultThreeMaterial = new THREE.MeshStandardMaterial({ roughness: 0.4, metalness: 0.3 });

// 2. Environment
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
camera.position.set(0, 5, 15);
camera.lookAt(0, 0, 0);

// Lighting
const ambientLight = new THREE.AmbientLight(0xffffff, 0.4);
scene.add(ambientLight);

const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8);
directionalLight.position.set(5, 10, 5);
directionalLight.castShadow = true; // Universal Standard: Shadows
scene.add(directionalLight);

// Ground Plane
const groundShape = new CANNON.Plane();
const groundBody = new CANNON.Body({ mass: 0, material: groundPhysicMaterial }); // Mass 0 for static ground
groundBody.addShape(groundShape);
groundBody.quaternion.setFromAxisAngle(new CANNON.Vec3(1, 0, 0), -Math.PI / 2); // Rotate to be horizontal
world.addBody(groundBody);

const groundGeometry = new THREE.PlaneGeometry(100, 100); // Large enough ground
const groundMesh = new THREE.Mesh(groundGeometry, defaultThreeMaterial);
groundMesh.rotation.x = -Math.PI / 2; // Align with Cannon.js body
groundMesh.receiveShadow = true; // Universal Standard: Shadows
scene.add(groundMesh);

// 3. Dynamic Actors
// Sphere
const sphereRadius = 0.5;
const sphereMass = 1; // kg
const sphereInitialPos = new CANNON.Vec3(0, 10, 0); // meters

const sphereShape = new CANNON.Sphere(sphereRadius);
const sphereBody = new CANNON.Body({ mass: sphereMass, shape: sphereShape, position: sphereInitialPos, material: ballPhysicMaterial });
world.addBody(sphereBody);

const sphereGeometry = new THREE.SphereGeometry(sphereRadius);
const sphereMesh = new THREE.Mesh(sphereGeometry, defaultThreeMaterial);
sphereMesh.castShadow = true; // Universal Standard: Shadows
scene.add(sphereMesh);

// 4. Logic & Interaction
const dt = 1 / 60; // Fixed time step for physics simulation

function render() {
    // Physics update
    world.step(dt);

    // Physics-Visual Sync
    sphereMesh.position.copy(sphereBody.position);
    sphereMesh.quaternion.copy(sphereBody.quaternion);

    // Ground mesh position/rotation sync is not needed as it's static (mass 0)
}

// The environment will call `render()` repeatedly.
// No GUI is created as per PHYSICS PROTOCOL.

// CRITICAL: The JS MUST end with a top-level return statement
return { scene, camera, world, render };
```

```json
{
  "title": "Bouncing Ball Simulation",
  "concept": "A single sphere bounces realistically on a static ground plane.",
  "description": "This simulation demonstrates gravity, restitution, and friction using Three.js for rendering and Cannon.js for physics. A sphere is dropped and bounces, with its physics state synchronized to its visual representation."
}
```