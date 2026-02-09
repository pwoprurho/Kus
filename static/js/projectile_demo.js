// --- Physics World ---
const world = new CANNON.World();
world.gravity.set(0, -9.81, 0);
world.broadphase = new CANNON.NaiveBroadphase();
world.solver.iterations = 10;
window.world = world;

// --- Scene Setup ---
const scene = new THREE.Scene();
scene.background = new THREE.Color(0x0a0a0f);

const camera = new THREE.PerspectiveCamera(60, window.innerWidth / window.innerHeight, 0.1, 1000);
camera.position.set(15, 10, 20);
camera.lookAt(0, 5, 0);

const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.shadowMap.enabled = true;

// --- Lighting ---
const ambientLight = new THREE.AmbientLight(0x404040, 0.5);
scene.add(ambientLight);

const dirLight = new THREE.DirectionalLight(0xffffff, 1);
dirLight.position.set(20, 50, 20);
dirLight.castShadow = true;
dirLight.shadow.mapSize.width = 2048;
dirLight.shadow.mapSize.height = 2048;
scene.add(dirLight);

// --- Materials ---
const material = new CANNON.Material();
const groundMaterial = new CANNON.Material();

// Contact material
const contactMat = new CANNON.ContactMaterial(groundMaterial, material, {
    friction: 0.4,
    restitution: 0.6 // Bounciness
});
world.addContactMaterial(contactMat);

// --- Ground ---
// Physics
const groundShape = new CANNON.Plane();
const groundBody = new CANNON.Body({ mass: 0, material: groundMaterial });
groundBody.addShape(groundShape);
groundBody.quaternion.setFromAxisAngle(new CANNON.Vec3(1, 0, 0), -Math.PI / 2);
world.addBody(groundBody);

// Visual
const planeGeo = new THREE.PlaneGeometry(100, 100);
const planeMat = new THREE.MeshStandardMaterial({
    color: 0x1a1a2e,
    roughness: 0.8,
    metalness: 0.2
});
const groundMesh = new THREE.Mesh(planeGeo, planeMat);
groundMesh.rotation.x = -Math.PI / 2;
groundMesh.receiveShadow = true;
scene.add(groundMesh);

const gridHelper = new THREE.GridHelper(100, 100, 0x2ecc71, 0x222222);
gridHelper.position.y = 0.01;
scene.add(gridHelper);

// --- Projectile ---
const radius = 0.8;
const shape = new CANNON.Sphere(radius);
const body = new CANNON.Body({
    mass: 5, // kg
    material: material,
    position: new CANNON.Vec3(-10, 2, 0),
    shape: shape
});

// Initial Velocity (Launch)
// 45 degrees, speed ~18 m/s
const velocity = new CANNON.Vec3(12, 12, 0);
body.velocity.copy(velocity);
world.addBody(body);

const sphereGeo = new THREE.SphereGeometry(radius, 32, 32);
const sphereMat = new THREE.MeshStandardMaterial({
    color: 0xff3366,
    roughness: 0.4,
    metalness: 0.5
});
const sphereMesh = new THREE.Mesh(sphereGeo, sphereMat);
sphereMesh.castShadow = true;
scene.add(sphereMesh);

// --- Trail ---
const trailGeo = new THREE.BufferGeometry();
const trailPositions = new Float32Array(500 * 3); // 500 points
trailGeo.setAttribute('position', new THREE.BufferAttribute(trailPositions, 3));
const trailMat = new THREE.LineBasicMaterial({ color: 0xffd700, transparent: true, opacity: 0.6 });
const trail = new THREE.Line(trailGeo, trailMat);
scene.add(trail);

let trailIdx = 0;

// --- Animation Loop ---
const timeStep = 1 / 60;
const clock = new THREE.Clock();

const controls = {
    getScene: () => scene,
    getCamera: () => camera,
    updateGravity: (g) => world.gravity.set(0, g, 0),
    reset: () => {
        body.position.set(-10, 2, 0);
        body.velocity.set(12, 12, 0);
        body.angularVelocity.set(0, 0, 0);
        // Reset trail
        trailIdx = 0;
        trailGeo.setDrawRange(0, 0);
    }
};

function render() {
    if (!window._animationCanceled) {
        const dt = clock.getDelta();
        world.step(timeStep, dt, 3);

        // Sync physics to visual
        sphereMesh.position.copy(body.position);
        sphereMesh.quaternion.copy(body.quaternion);

        // Update trail
        if (trailIdx < 500) {
            const positions = trail.geometry.attributes.position.array;
            positions[trailIdx * 3] = body.position.x;
            positions[trailIdx * 3 + 1] = body.position.y;
            positions[trailIdx * 3 + 2] = body.position.z;
            trailIdx++;
            trail.geometry.setDrawRange(0, trailIdx);
            trail.geometry.attributes.position.needsUpdate = true;
        }
    }
    return controls;
}

// Return the scene and camera controls to the sandbox
return {
    scene: scene,
    camera: camera,
    rendererParameters: { antialias: true },
    render: render, // Using standardized render hook
    controls: controls
};
