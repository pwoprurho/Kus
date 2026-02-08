import * as THREE from 'three';
import * as CANNON from 'cannon-es';

let scene, camera, renderer, world;
let cannonBody, cannonMesh;
let trajectoryPoints = [];
let trajectoryLine;
let velocityXText, velocityYText, velocityZText;
let initialVelocityArrow;
let cannonObject;

const params = {
    launchAngle: 45,  // degrees
    muzzleVelocity: 50, // m/s
    airResistance: 0.01 // drag coefficient
};

const init = () => {
    // Scene setup
    scene = new THREE.Scene();
    scene.background = new THREE.Color(0x1a1a2e);

    // Camera
    camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
    camera.position.set(0, 10, 30);
    camera.lookAt(0, 5, 0);

    // Renderer
    renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.setPixelRatio(window.devicePixelRatio);
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    document.body.appendChild(renderer.domElement);

    // Cannon-es world
    world = new CANNON.World();
    world.gravity.set(0, -9.81, 0);
    world.broadphase = new CANNON.SAPBroadphase(world);
    world.solver.iterations = 10;

    // Lights
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.3);
    scene.add(ambientLight);

    const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8);
    directionalLight.position.set(10, 20, 10);
    directionalLight.castShadow = true;
    directionalLight.shadow.mapSize.width = 2048;
    directionalLight.shadow.mapSize.height = 2048;
    directionalLight.shadow.camera.near = 0.5;
    directionalLight.shadow.camera.far = 50;
    directionalLight.shadow.camera.left = -20;
    directionalLight.shadow.camera.right = 20;
    directionalLight.shadow.camera.top = 20;
    directionalLight.shadow.camera.bottom = -20;
    scene.add(directionalLight);
    scene.add(directionalLight.target);

    // Ground Plane
    const groundShape = new CANNON.Plane();
    const groundBody = new CANNON.Body({ mass: 0 });
    groundBody.addShape(groundShape);
    groundBody.quaternion.setFromEuler(-Math.PI / 2, 0, 0);
    world.addBody(groundBody);

    const groundMesh = new THREE.Mesh(
        new THREE.PlaneGeometry(100, 100),
        new THREE.MeshStandardMaterial({ color: 0x22223b, side: THREE.DoubleSide, roughness: 0.8, metalness: 0.2 })
    );
    groundMesh.receiveShadow = true;
    groundMesh.rotation.x = -Math.PI / 2;
    scene.add(groundMesh);

    // Grid Helper
    const gridHelper = new THREE.GridHelper(100, 100, 0x4a4e69, 0x4a4e69);
    scene.add(gridHelper);

    // Cannon Model
    const cannonGeometry = new THREE.CylinderGeometry(0.5, 0.7, 3, 32);
    const cannonMaterial = new THREE.MeshStandardMaterial({ color: 0x5f0f40, roughness: 0.6, metalness: 0.4 });
    cannonObject = new THREE.Mesh(cannonGeometry, cannonMaterial);
    cannonObject.position.set(0, 1.5, -13);
    cannonObject.rotation.z = Math.PI / 2; // Initial horizontal orientation
    cannonObject.castShadow = true;
    scene.add(cannonObject);

    // Velocity text overlays
    const createText = (position, color = 0xffffff) => {
        const canvas = document.createElement('canvas');
        const context = canvas.getContext('2d');
        context.font = 'Bold 40px Arial';
        context.fillStyle = '#ffffff';
        context.textAlign = 'center';
        context.fillText('Loading...', 128, 128);

        const texture = new THREE.CanvasTexture(canvas);
        const spriteMaterial = new THREE.SpriteMaterial({ map: texture });
        const sprite = new THREE.Sprite(spriteMaterial);
        sprite.scale.set(4, 2, 1);
        sprite.position.copy(position);
        scene.add(sprite);
        return sprite;
    };

    velocityXText = createText(new THREE.Vector3(-10, 8, -10));
    velocityYText = createText(new THREE.Vector3(-10, 7, -10));
    velocityZText = createText(new THREE.Vector3(-10, 6, -10));

    // Initial setup for the cannon and firing
    reset();

    // Handle window resize
    window.addEventListener('resize', () => {
        camera.aspect = window.innerWidth / window.innerHeight;
        camera.updateProjectionMatrix();
        renderer.setSize(window.innerWidth, window.innerHeight);
    });
};

const updateText = (sprite, text) => {
    const canvas = sprite.material.map.image;
    const context = canvas.getContext('2d');
    context.clearRect(0, 0, canvas.width, canvas.height);
    context.fillText(text, 128, 128);
    sprite.material.map.needsUpdate = true;
};

const fireProjectile = () => {
    if (cannonMesh) {
        scene.remove(cannonMesh);
        world.removeBody(cannonBody);
    }
    if (trajectoryLine) {
        scene.remove(trajectoryLine);
        trajectoryPoints = [];
    }
    if (initialVelocityArrow) {
        scene.remove(initialVelocityArrow);
    }

    // Projectile (glowing orb)
    const sphereGeometry = new THREE.SphereGeometry(0.5, 32, 32);
    const sphereMaterial = new THREE.MeshStandardMaterial({
        color: 0xff4081, // Pinkish-red
        emissive: 0xff4081, // Glowing effect
        emissiveIntensity: 1.5,
        roughness: 0.2,
        metalness: 0.1
    });
    cannonMesh = new THREE.Mesh(sphereGeometry, sphereMaterial);
    cannonMesh.castShadow = true;
    cannonMesh.position.set(0, 2, -12); // Start slightly above the cannon muzzle
    scene.add(cannonMesh);

    // Point light inside the orb for extra glow
    const pointLight = new THREE.PointLight(0xff4081, 1.0, 10);
    pointLight.position.set(0, 0, 0);
    cannonMesh.add(pointLight);

    const sphereShape = new CANNON.Sphere(0.5);
    cannonBody = new CANNON.Body({
        mass: 1,
        position: new CANNON.Vec3(0, 2, -12)
    });
    cannonBody.addShape(sphereShape);
    cannonBody.linearDamping = params.airResistance; // Air resistance
    world.addBody(cannonBody);

    // Calculate initial velocity components
    const angleRad = params.launchAngle * Math.PI / 180;
    const velX = 0; // Assuming firing along Z axis, not X
    const velY = params.muzzleVelocity * Math.sin(angleRad);
    const velZ = params.muzzleVelocity * Math.cos(angleRad);
    cannonBody.velocity.set(velX, velY, velZ);

    // Update cannon orientation to match launch angle
    cannonObject.rotation.z = Math.PI / 2 - angleRad;

    // Initial velocity arrow helper
    const origin = new THREE.Vector3(cannonMesh.position.x, cannonMesh.position.y, cannonMesh.position.z);
    const direction = new THREE.Vector3(velX, velY, velZ).normalize();
    const length = params.muzzleVelocity / 5; // Scale arrow length for visibility
    const hex = 0x00ff00;
    initialVelocityArrow = new THREE.ArrowHelper(direction, origin, length, hex);
    scene.add(initialVelocityArrow);

    trajectoryPoints = [];
};

const animate = () => {
    requestAnimationFrame(animate);

    world.step(1 / 60); // Update physics 60 times per second

    if (cannonMesh && cannonBody) {
        cannonMesh.position.copy(cannonBody.position);
        cannonMesh.quaternion.copy(cannonBody.quaternion);

        // Add current position to trajectory points
        trajectoryPoints.push(cannonMesh.position.clone());

        // Update trajectory line
        if (trajectoryPoints.length > 1) {
            if (trajectoryLine) scene.remove(trajectoryLine);
            const geometry = new THREE.BufferGeometry().setFromPoints(trajectoryPoints);
            const material = new THREE.LineBasicMaterial({ color: 0x8a2be2, linewidth: 2 }); // Blue-violet path
            trajectoryLine = new THREE.Line(geometry, material);
            scene.add(trajectoryLine);
        }

        // Update velocity text
        updateText(velocityXText, `Vx: ${cannonBody.velocity.x.toFixed(2)} m/s`);
        updateText(velocityYText, `Vy: ${cannonBody.velocity.y.toFixed(2)} m/s`);
        updateText(velocityZText, `Vz: ${cannonBody.velocity.z.toFixed(2)} m/s`);

        // Remove projectile if it goes below the ground
        if (cannonMesh.position.y < -5) {
            scene.remove(cannonMesh);
            world.removeBody(cannonBody);
            cannonMesh = null;
            cannonBody = null;
            if (initialVelocityArrow) {
                scene.remove(initialVelocityArrow);
                initialVelocityArrow = null;
            }
        }
    }

    renderer.render(scene, camera);
};

init();
animate();

// Exposed functions for interactivity
const updateGravity = (x, y, z) => {
    world.gravity.set(x, y, z);
};

const updateObjectParameter = (index, param, value) => {
    // For this simulation, we're using global parameters directly
    if (params.hasOwnProperty(param)) {
        params[param] = value;
        // Re-fire projectile with new parameters immediately for interactive feedback
        fireProjectile();
    }
};

const reset = () => {
    fireProjectile(); // Reset by re-firing the projectile with current parameters
};

return { updateGravity, updateObjectParameter, reset };