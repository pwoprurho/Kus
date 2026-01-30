# routes/physics_sandbox.py
"""
Physics Sandbox API Routes
Handles experiment generation, validation, and execution.
"""

import json
import re
from flask import Blueprint, request, jsonify, render_template
from core.physics_ai import PhysicsAIEngine
from core.validator import PhysicsCodeValidator
from core.security import sign_forensic_trace
import datetime

physics_bp = Blueprint('physics', __name__)

# Initialize components
ai_engine = PhysicsAIEngine()
validator = PhysicsCodeValidator()

# Template matching patterns for instant responses
TEMPLATE_PATTERNS = {
    "free_fall": [
        r'fall(ing|ing\s+from)',
        r'drop(ped|\s+from)',
        r'free\s+fall'
    ],
    "pendulum": [
        r'pendulum',
        r'swing(ing|ing\s+back)',
        r'oscillat'
    ],
    "collision": [
        r'coll(ide|ision|iding)',
        r'crash',
        r'impact'
    ],
    "projectile": [
        r'projectile',
        r'throw(n|ing)?',
        r'launch(ed|ing)?'
    ],
    "inclined_plane": [
        r'inclined',
        r'ramp',
        r'slope'
    ],
    "spring": [
        r'spring',
        r'hooke',
        r'elastic'
    ]
}

# Pre-built experiment templates with full Three.js code
PREBUILT_TEMPLATES = {
    "free_fall": {
        "title": "Free Fall Experiment",
        "description": "Ball falling under gravity",
        "concept": "Free Fall",
        "threejs_code": '''
(function() {
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x1a1a2e);
    
    const camera = new THREE.PerspectiveCamera(60, window.innerWidth / window.innerHeight, 0.1, 1000);
    camera.position.set(0, 8, 15);
    camera.lookAt(0, 3, 0);
    
    const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.shadowMap.enabled = true;
    
    const ambientLight = new THREE.AmbientLight(0x404040, 0.5);
    scene.add(ambientLight);
    
    const directionalLight = new THREE.DirectionalLight(0xffffff, 1);
    directionalLight.position.set(5, 15, 10);
    directionalLight.castShadow = true;
    scene.add(directionalLight);
    
    const world = new CANNON.World();
    world.gravity.set(0, -9.81, 0);
    
    const defaultMaterial = new CANNON.Material('default');
    const defaultContactMaterial = new CANNON.ContactMaterial(defaultMaterial, defaultMaterial, { friction: 0.3, restitution: 0.5 });
    world.addContactMaterial(defaultContactMaterial);
    
    // Ground
    const groundGeo = new THREE.PlaneGeometry(20, 20);
    const groundMat = new THREE.MeshStandardMaterial({ color: 0x2a2a3e, metalness: 0.1, roughness: 0.8 });
    const ground = new THREE.Mesh(groundGeo, groundMat);
    ground.rotation.x = -Math.PI / 2;
    ground.receiveShadow = true;
    scene.add(ground);
    
    const groundBody = new CANNON.Body({ mass: 0, material: defaultMaterial });
    groundBody.addShape(new CANNON.Plane());
    groundBody.quaternion.setFromEuler(-Math.PI / 2, 0, 0);
    world.addBody(groundBody);
    
    // Ball
    const ballRadius = 0.5;
    const ballGeo = new THREE.SphereGeometry(ballRadius, 32, 32);
    const ballMat = new THREE.MeshStandardMaterial({ color: 0xe74c3c, metalness: 0.3, roughness: 0.4 });
    const ball = new THREE.Mesh(ballGeo, ballMat);
    ball.castShadow = true;
    ball.position.set(0, 10, 0);
    scene.add(ball);
    
    const ballBody = new CANNON.Body({ mass: 1, material: defaultMaterial });
    ballBody.addShape(new CANNON.Sphere(ballRadius));
    ballBody.position.set(0, 10, 0);
    world.addBody(ballBody);
    
    // Grid helper
    const grid = new THREE.GridHelper(20, 20, 0x444444, 0x333333);
    grid.position.y = 0.01;
    scene.add(grid);
    
    const timeStep = 1 / 60;
    function animate() {
        requestAnimationFrame(animate);
        world.step(timeStep);
        ball.position.copy(ballBody.position);
        ball.quaternion.copy(ballBody.quaternion);
        renderer.render(scene, camera);
    }
    
    window.addEventListener('resize', () => {
        camera.aspect = window.innerWidth / window.innerHeight;
        camera.updateProjectionMatrix();
        renderer.setSize(window.innerWidth, window.innerHeight);
    });
    
    animate();
    
    return {
        updateGravity: (x, y, z) => world.gravity.set(x, y, z),
        updateObjectParameter: (objId, param, val) => {
            if (objId === 0) { // Ball is index 0
                if (param === 'mass') {
                    ballBody.mass = val;
                    ballBody.updateMassProperties();
                } else if (param === 'radius') {
                    // Update physics shape
                    ballBody.shapes[0].radius = val;
                    ballBody.updateBoundingRadius();
                    // Update visual
                    ball.scale.set(val/0.5, val/0.5, val/0.5);
                } else if (param === 'height') {
                    ballBody.position.y = val;
                    ballBody.velocity.set(0, 0, 0);
                    ballBody.angularVelocity.set(0, 0, 0);
                }
            }
        },
        reset: () => {
            ballBody.position.set(0, 10, 0);
            ballBody.velocity.set(0, 0, 0);
            ballBody.angularVelocity.set(0, 0, 0);
        }
    };
})();
''',
        "physics_config": {"gravity": [0, -9.81, 0], "timeScale": 1.0},
        "objects": [
            {
                "id": "ball", 
                "name": "Ball", 
                "type": "sphere", 
                "physics": {"mass": 1},
                "adjustable": {
                    "height": {"min": 5, "max": 20, "step": 1, "value": 10},
                    "mass": {"min": 0.1, "max": 10, "step": 0.1, "value": 1},
                    "radius": {"min": 0.2, "max": 2, "step": 0.1, "value": 0.5}
                }
            }
        ],
        "parameters": {"gravity": {"min": 1, "max": 20, "value": 9.81}},
        "estimated_runtime": 3000
    },
    "pendulum": {
        "title": "Simple Pendulum",
        "description": "Pendulum demonstrating periodic motion",
        "concept": "Simple Harmonic Motion",
        "threejs_code": '''
(function() {
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x1a1a2e);
    
    const camera = new THREE.PerspectiveCamera(60, window.innerWidth / window.innerHeight, 0.1, 1000);
    camera.position.set(5, 5, 10);
    camera.lookAt(0, 0, 0);
    
    const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.shadowMap.enabled = true;
    
    const ambientLight = new THREE.AmbientLight(0x404040, 0.5);
    scene.add(ambientLight);
    
    const directionalLight = new THREE.DirectionalLight(0xffffff, 1);
    directionalLight.position.set(5, 10, 5);
    directionalLight.castShadow = true;
    scene.add(directionalLight);
    
    const world = new CANNON.World();
    world.gravity.set(0, -9.81, 0);
    world.broadphase = new CANNON.NaiveBroadphase();
    
    const defaultMaterial = new CANNON.Material('default');
    
    // Pivot point (static)
    const pivotBody = new CANNON.Body({ mass: 0 });
    pivotBody.position.set(0, 4, 0);
    world.addBody(pivotBody);
    
    // Pendulum bob
    const bobRadius = 0.3;
    const stringLength = 2;
    const bobGeo = new THREE.SphereGeometry(bobRadius, 32, 32);
    const bobMat = new THREE.MeshStandardMaterial({ color: 0x3498db, metalness: 0.3, roughness: 0.4 });
    const bob = new THREE.Mesh(bobGeo, bobMat);
    bob.castShadow = true;
    scene.add(bob);
    
    const bobBody = new CANNON.Body({ mass: 1, material: defaultMaterial });
    bobBody.addShape(new CANNON.Sphere(bobRadius));
    bobBody.position.set(stringLength, 2, 0);
    bobBody.linearDamping = 0.01;
    world.addBody(bobBody);
    
    // Use DistanceConstraint for easier length updates
    const constraint = new CANNON.DistanceConstraint(pivotBody, bobBody, stringLength);
    world.addConstraint(constraint);
    
    // String visualization
    const stringGeo = new THREE.BufferGeometry();
    const stringMat = new THREE.LineBasicMaterial({ color: 0x888888 });
    const stringLine = new THREE.Line(stringGeo, stringMat);
    scene.add(stringLine);
    
    // Pivot point visualization
    const pivotGeo = new THREE.SphereGeometry(0.1, 16, 16);
    const pivotMat = new THREE.MeshBasicMaterial({ color: 0x888888 });
    const pivotMesh = new THREE.Mesh(pivotGeo, pivotMat);
    pivotMesh.position.set(0, 4, 0);
    scene.add(pivotMesh);
    
    const timeStep = 1 / 60;
    function animate() {
        requestAnimationFrame(animate);
        world.step(timeStep);
        
        bob.position.copy(bobBody.position);
        bob.quaternion.copy(bobBody.quaternion);
        
        // Update string visualization
        const positions = new Float32Array([
            0, 4, 0,
            bob.position.x, bob.position.y, bob.position.z
        ]);
        stringGeo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
        
        renderer.render(scene, camera);
    }
    
    window.addEventListener('resize', () => {
        camera.aspect = window.innerWidth / window.innerHeight;
        camera.updateProjectionMatrix();
        renderer.setSize(window.innerWidth, window.innerHeight);
    });
    
    animate();
    
    return {
        updateGravity: (x, y, z) => world.gravity.set(x, y, z),
        updateObjectParameter: (objId, param, val) => {
            if (objId === 0) { // Bob is index 0
                if (param === 'mass') {
                    bobBody.mass = val;
                    bobBody.updateMassProperties();
                } else if (param === 'length') {
                    constraint.distance = val;
                    // Move bob to maintain angle if possible, or just let it snap
                }
            }
        },
        reset: () => {
            const len = constraint.distance;
            // 45 degree start: x = L*sin(45), y = pivotY - L*cos(45)
            const angle = Math.PI / 4;
            bobBody.position.set(len * Math.sin(angle), 4 - len * Math.cos(angle), 0);
            bobBody.velocity.set(0, 0, 0);
            bobBody.angularVelocity.set(0, 0, 0);
        }
    };
})();
''',
        "physics_config": {"gravity": [0, -9.81, 0], "timeScale": 1.0},
        "objects": [
            {
                "id": "bob", 
                "name": "Pendulum Bob", 
                "type": "sphere",
                "adjustable": {
                    "length": {"min": 1, "max": 5, "step": 0.1, "value": 2},
                    "mass": {"min": 0.1, "max": 5, "step": 0.1, "value": 1}
                }
            }
        ],
        "parameters": {"gravity": {"min": 1, "max": 20, "value": 9.81}},
        "estimated_runtime": 5000
    },
    "collision": {
        "title": "Elastic Collision",
        "description": "Two balls colliding with equal mass",
        "concept": "Momentum Conservation",
        "threejs_code": '''
(function() {
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x1a1a2e);
    
    const camera = new THREE.PerspectiveCamera(60, window.innerWidth / window.innerHeight, 0.1, 1000);
    camera.position.set(0, 8, 20);
    camera.lookAt(0, 1, 0);
    
    const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.shadowMap.enabled = true;
    
    const ambientLight = new THREE.AmbientLight(0x404040, 0.5);
    scene.add(ambientLight);
    
    const directionalLight = new THREE.DirectionalLight(0xffffff, 1);
    directionalLight.position.set(0, 15, 10);
    directionalLight.castShadow = true;
    scene.add(directionalLight);
    
    const world = new CANNON.World();
    world.gravity.set(0, -9.81, 0);
    
    const defaultMaterial = new CANNON.Material('default');
    const bouncyMaterial = new CANNON.ContactMaterial(defaultMaterial, defaultMaterial, { friction: 0.3, restitution: 0.95 });
    world.addContactMaterial(bouncyMaterial);
    
    // Ground
    const groundGeo = new THREE.PlaneGeometry(30, 10);
    const groundMat = new THREE.MeshStandardMaterial({ color: 0x2a2a3e, metalness: 0.1, roughness: 0.8 });
    const ground = new THREE.Mesh(groundGeo, groundMat);
    ground.rotation.x = -Math.PI / 2;
    ground.receiveShadow = true;
    scene.add(ground);
    
    const groundBody = new CANNON.Body({ mass: 0, material: defaultMaterial });
    groundBody.addShape(new CANNON.Plane());
    groundBody.quaternion.setFromEuler(-Math.PI / 2, 0, 0);
    world.addBody(groundBody);
    
    const ballRadius = 0.5;
    
    // Ball 1 (red)
    const ball1Geo = new THREE.SphereGeometry(ballRadius, 32, 32);
    const ball1Mat = new THREE.MeshStandardMaterial({ color: 0xe74c3c, metalness: 0.3, roughness: 0.4 });
    const ball1 = new THREE.Mesh(ball1Geo, ball1Mat);
    ball1.castShadow = true;
    scene.add(ball1);
    
    const ball1Body = new CANNON.Body({ mass: 1, material: defaultMaterial });
    ball1Body.addShape(new CANNON.Sphere(ballRadius));
    ball1Body.position.set(-8, ballRadius + 0.5, 0);
    ball1Body.velocity.set(8, 0, 0);
    world.addBody(ball1Body);
    
    // Ball 2 (blue)
    const ball2Geo = new THREE.SphereGeometry(ballRadius, 32, 32);
    const ball2Mat = new THREE.MeshStandardMaterial({ color: 0x3498db, metalness: 0.3, roughness: 0.4 });
    const ball2 = new THREE.Mesh(ball2Geo, ball2Mat);
    ball2.castShadow = true;
    scene.add(ball2);
    
    const ball2Body = new CANNON.Body({ mass: 1, material: defaultMaterial });
    ball2Body.addShape(new CANNON.Sphere(ballRadius));
    ball2Body.position.set(8, ballRadius + 0.5, 0);
    ball2Body.velocity.set(-8, 0, 0);
    world.addBody(ball2Body);
    
    const grid = new THREE.GridHelper(30, 30, 0x444444, 0x333333);
    grid.position.y = 0.01;
    scene.add(grid);
    
    const timeStep = 1 / 60;
    function animate() {
        requestAnimationFrame(animate);
        world.step(timeStep);
        
        ball1.position.copy(ball1Body.position);
        ball1.quaternion.copy(ball1Body.quaternion);
        ball2.position.copy(ball2Body.position);
        ball2.quaternion.copy(ball2Body.quaternion);
        
        renderer.render(scene, camera);
    }
    
    window.addEventListener('resize', () => {
        camera.aspect = window.innerWidth / window.innerHeight;
        camera.updateProjectionMatrix();
        renderer.setSize(window.innerWidth, window.innerHeight);
    });
    
    animate();
    
    return {
        updateGravity: (x, y, z) => world.gravity.set(x, y, z),
        updateObjectParameter: (objId, param, val) => {
            if (param === 'restitution') {
                world.defaultContactMaterial.restitution = val;
            } else if (objId === 0) { // Ball 1
                if (param === 'mass') {
                    ball1Body.mass = val;
                    ball1Body.updateMassProperties();
                } else if (param === 'initial_velocity') {
                    ball1Body.velocity.set(val, 0, 0);
                }
            } else if (objId === 1) { // Ball 2
                if (param === 'mass') {
                    ball2Body.mass = val;
                    ball2Body.updateMassProperties();
                } else if (param === 'initial_velocity') {
                    ball2Body.velocity.set(-val, 0, 0);
                }
            }
        },
        reset: () => {
            ball1Body.position.set(-8, ballRadius + 0.5, 0);
            ball1Body.velocity.set(8, 0, 0);
            ball1Body.angularVelocity.set(0, 0, 0);
            ball2Body.position.set(8, ballRadius + 0.5, 0);
            ball2Body.velocity.set(-8, 0, 0);
            ball2Body.angularVelocity.set(0, 0, 0);
        }
    };
})();
''',
        "physics_config": {"gravity": [0, -9.81, 0], "timeScale": 1.0},
        "objects": [
            {
                "id": "ball1", 
                "name": "Red Ball", 
                "type": "sphere",
                "adjustable": {
                    "mass": {"min": 0.1, "max": 10, "step": 0.1, "value": 1},
                    "initial_velocity": {"min": 1, "max": 20, "step": 1, "value": 8}
                }
            },
            {
                "id": "ball2", 
                "name": "Blue Ball", 
                "type": "sphere",
                "adjustable": {
                    "mass": {"min": 0.1, "max": 10, "step": 0.1, "value": 1},
                    "initial_velocity": {"min": 1, "max": 20, "step": 1, "value": 8}
                }
            }
        ],
        "parameters": {
            "gravity": {"min": 1, "max": 20, "value": 9.81},
            "restitution": {"min": 0, "max": 1, "step": 0.05, "value": 0.95}
        },
        "estimated_runtime": 4000
    },
    "projectile": {
        "title": "Projectile Motion",
        "description": "Ball launched at an angle",
        "concept": "2D Kinematics",
        "threejs_code": '''
(function() {
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x1a1a2e);
    
    const camera = new THREE.PerspectiveCamera(60, window.innerWidth / window.innerHeight, 0.1, 1000);
    camera.position.set(15, 10, 25);
    camera.lookAt(10, 5, 0);
    
    const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.shadowMap.enabled = true;
    
    const ambientLight = new THREE.AmbientLight(0x404040, 0.5);
    scene.add(ambientLight);
    
    const directionalLight = new THREE.DirectionalLight(0xffffff, 1);
    directionalLight.position.set(10, 20, 10);
    directionalLight.castShadow = true;
    scene.add(directionalLight);
    
    const world = new CANNON.World();
    world.gravity.set(0, -9.81, 0);
    
    const defaultMaterial = new CANNON.Material('default');
    
    // Ground
    const groundGeo = new THREE.PlaneGeometry(100, 100);
    const groundMat = new THREE.MeshStandardMaterial({ color: 0x2a2a3e });
    const ground = new THREE.Mesh(groundGeo, groundMat);
    ground.rotation.x = -Math.PI / 2;
    ground.receiveShadow = true;
    scene.add(ground);
    
    const groundBody = new CANNON.Body({ mass: 0, material: defaultMaterial });
    groundBody.addShape(new CANNON.Plane());
    groundBody.quaternion.setFromEuler(-Math.PI / 2, 0, 0);
    world.addBody(groundBody);
    
    // Ball
    const ballRadius = 0.5;
    const ballGeo = new THREE.SphereGeometry(ballRadius, 32, 32);
    const ballMat = new THREE.MeshStandardMaterial({ color: 0xf1c40f });
    const ball = new THREE.Mesh(ballGeo, ballMat);
    ball.castShadow = true;
    scene.add(ball);
    
    const ballBody = new CANNON.Body({ mass: 1, material: defaultMaterial });
    ballBody.addShape(new CANNON.Sphere(ballRadius));
    ballBody.position.set(0, ballRadius, 0);
    
    // Launch: 45 degrees, velocity 15
    const v0 = 15;
    const angle = Math.PI / 4;
    ballBody.velocity.set(v0 * Math.cos(angle), v0 * Math.sin(angle), 0);
    world.addBody(ballBody);
    
    const grid = new THREE.GridHelper(100, 50, 0x444444, 0x333333);
    grid.position.y = 0.01;
    scene.add(grid);
    
    const timeStep = 1 / 60;
    function animate() {
        requestAnimationFrame(animate);
        world.step(timeStep);
        ball.position.copy(ballBody.position);
        ball.quaternion.copy(ballBody.quaternion);
        renderer.render(scene, camera);
    }
    
    window.addEventListener('resize', () => {
        camera.aspect = window.innerWidth / window.innerHeight;
        camera.updateProjectionMatrix();
        renderer.setSize(window.innerWidth, window.innerHeight);
    });
    
    animate();
    
    // Current launch params
    let currentV0 = v0;
    let currentAngle = angle;
    let currentHeight = ballRadius;

    return {
        updateGravity: (x, y, z) => world.gravity.set(x, y, z),
        updateObjectParameter: (objId, param, val) => {
            if (objId === 0) { // Ball is index 0
                if (param === 'launch_angle') {
                    currentAngle = (val * Math.PI) / 180;
                } else if (param === 'initial_velocity') {
                    currentV0 = val;
                } else if (param === 'height') {
                    currentHeight = val;
                }
                // Apply immediately to current state if wanted, or just on reset
                ballBody.position.set(0, currentHeight, 0);
                ballBody.velocity.set(currentV0 * Math.cos(currentAngle), currentV0 * Math.sin(currentAngle), 0);
            }
        },
        reset: () => {
            ballBody.position.set(0, currentHeight, 0);
            ballBody.velocity.set(currentV0 * Math.cos(currentAngle), currentV0 * Math.sin(currentAngle), 0);
            ballBody.angularVelocity.set(0, 0, 0);
        }
    };
})();
''',
        "physics_config": {"gravity": [0, -9.81, 0], "timeScale": 1.0},
        "objects": [
            {
                "id": "ball", 
                "name": "Projectile Ball", 
                "type": "sphere",
                "adjustable": {
                    "launch_angle": {"min": 0, "max": 90, "step": 1, "value": 45},
                    "initial_velocity": {"min": 5, "max": 40, "step": 1, "value": 15},
                    "height": {"min": 0.5, "max": 20, "step": 0.5, "value": 0.5}
                }
            }
        ],
        "parameters": {"gravity": {"min": 1, "max": 20, "value": 9.81}},
        "estimated_runtime": 5000
    }
}


def match_template(description: str):
    """Check if description matches a known template pattern."""
    desc_lower = description.lower()
    
    for template_id, patterns in TEMPLATE_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, desc_lower):
                if template_id in PREBUILT_TEMPLATES:
                    return template_id, PREBUILT_TEMPLATES[template_id]
    
    return None, None


@physics_bp.route("/physics-mvp")
def physics_mvp_view():
    """Renders the Physics Sandbox MVP interface."""
    return render_template('physics_mvp.html')

@physics_bp.route("/physics-sandbox")
def physics_sandbox_view():
    """Renders the Physics Sandbox interface."""
    return render_template('physics_sandbox.html')


@physics_bp.route("/api/physics/generate", methods=["POST"])
def generate_experiment():
    """
    Takes natural language experiment description.
    Returns: Pre-built template if available, else AI-generated code.
    """
    try:
        data = request.get_json()
        description = data.get('description', '').strip()
        show_code = data.get('options', {}).get('show_code', True)
        
        if not description:
            return jsonify({
                "success": False,
                "error": "Please describe an experiment to visualize"
            }), 400
        
        # FIRST: Check for pre-built template (instant response)
        template_id, template = match_template(description)
        
        if template_id and template:
            return jsonify({
                "success": True,
                "experiment": {
                    "title": template["title"],
                    "description": template["description"],
                    "concept": template["concept"],
                    "threejs_code": template["threejs_code"] if show_code else None,
                    "physics_config": template["physics_config"],
                    "objects": template["objects"],
                    "parameters": template["parameters"],
                    "estimated_runtime": template["estimated_runtime"]
                },
                "template_used": template_id,
                "source": "prebuilt",
                "validation": {"passed": True, "security_level": "high"}
            })
        
        # SECOND: Fall back to AI generation for custom experiments
        # Generate experiment using AI
        result = ai_engine.generate_experiment_code(description)
        
        if result.get('errors'):
            return jsonify({
                "success": False,
                "error": "Could not understand experiment description",
                "details": result['errors'],
                "suggestion": "Try describing the experiment more simply"
            }), 400
        
        # Validate generated code
        validation = validator.validate(result.get('threejs_code', ''))
        
        if not validation['valid']:
            return jsonify({
                "success": False,
                "error": "Generated code failed security validation",
                "issues": validation['issues']
            }), 500
        
        response = {
            "success": True,
            "experiment": {
                "title": result.get('title', 'Physics Experiment'),
                "description": result.get('description', description),
                "concept": result.get('concept', 'Physics'),
                "threejs_code": result['threejs_code'] if show_code else None,
                "physics_config": result.get('physics_config', {}),
                "objects": result.get('objects', []),
                "parameters": result.get('parameters', {}),
                "estimated_runtime": result.get('estimated_runtime', 5000)
            },
            "validation": {
                "passed": True,
                "security_level": validation.get('security_level', 'high')
            }
        }
        
        return jsonify(response)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": f"Server error: {str(e)}"
        }), 500


@physics_bp.route("/api/physics/validate", methods=["POST"])
def validate_code():
    """
    Validates AI-generated code for security and correctness.
    """
    try:
        data = request.get_json()
        code = data.get('code', '')
        
        if not code:
            return jsonify({
                "valid": False,
                "issues": ["No code provided"]
            }), 400
        
        result = validator.validate(code)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            "valid": False,
            "issues": [str(e)]
        }), 500


# Sample experiment prompts for the examples API
EXPERIMENT_EXAMPLES = {
    "simple": [
        {
            "prompt": "A ball dropped from 10 meters with gravity",
            "concept": "Free Fall",
            "description": "Observe how objects fall under gravity"
        },
        {
            "prompt": "Two balls colliding head-on with equal mass",
            "concept": "Elastic Collision",
            "description": "Momentum and energy conservation"
        },
        {
            "prompt": "A ball rolling down an inclined plane",
            "concept": "Inclined Plane",
            "description": "Gravity components and friction"
        },
        {
            "prompt": "A pendulum swinging with length 2 meters",
            "concept": "Simple Pendulum",
            "description": "Periodic motion and gravity"
        }
    ],
    "intermediate": [
        {
            "prompt": "A spring-mass system with spring constant 50 N/m and mass 2 kg",
            "concept": "Hooke's Law",
            "description": "Simple harmonic motion"
        },
        {
            "prompt": "A projectile launched at 30 degrees with 20 m/s initial velocity",
            "concept": "Projectile Motion",
            "description": "Trajectory and parabolic path"
        },
        {
            "prompt": "Three balls in a chain collision",
            "concept": "Momentum Transfer",
            "description": "Newton's cradle simulation"
        }
    ]
}


@physics_bp.route("/api/physics/examples", methods=["GET"])
def get_examples():
    """
    Returns sample experiment prompts for students.
    """
    complexity = request.args.get('complexity', 'all')
    
    if complexity == 'all':
        return jsonify(EXPERIMENT_EXAMPLES)
    elif complexity in EXPERIMENT_EXAMPLES:
        return jsonify({complexity: EXPERIMENT_EXAMPLES[complexity]})
    else:
        return jsonify({
            "simple": EXPERIMENT_EXAMPLES["simple"],
            "intermediate": EXPERIMENT_EXAMPLES["intermediate"]
        })


@physics_bp.route("/api/physics/quick-templates", methods=["GET"])
def get_quick_templates():
    """
    Returns pre-built experiment templates for quick start.
    """
    templates = {
        "free_fall": {
            "name": "Free Fall",
            "description": "Ball dropped from height",
            "config": {
                "objects": [
                    {
                        "type": "sphere",
                        "name": "ball",
                        "position": [0, 10, 0],
                        "params": {"radius": 0.5},
                        "physics": {"mass": 1, "restitution": 0.5}
                    },
                    {
                        "type": "plane",
                        "name": "ground",
                        "position": [0, 0, 0],
                        "params": {"width": 20, "height": 20},
                        "physics": {"mass": 0, "friction": 0.5}
                    }
                ],
                "simulation": {
                    "gravity": [0, -9.81, 0],
                    "timeScale": 1.0
                }
            }
        },
        "pendulum": {
            "name": "Simple Pendulum",
            "description": "Pendulum swinging under gravity",
            "config": {
                "objects": [
                    {
                        "type": "sphere",
                        "name": "bob",
                        "position": [0, -2, 0],
                        "params": {"radius": 0.3},
                        "physics": {"mass": 1}
                    }
                ],
                "constraints": [
                    {
                        "type": "point_to_point",
                        "body1": "pivot",
                        "body2": "bob",
                        "pivotA": [0, 0, 0],
                        "pivotB": [0, 2, 0]
                    }
                ],
                "simulation": {
                    "gravity": [0, -9.81, 0],
                    "timeScale": 1.0
                }
            }
        },
        "collision": {
            "name": "Elastic Collision",
            "description": "Two balls colliding",
            "config": {
                "objects": [
                    {
                        "type": "sphere",
                        "name": "ball1",
                        "position": [-5, 0.5, 0],
                        "params": {"radius": 0.5},
                        "physics": {"mass": 1, "velocity": [5, 0, 0], "restitution": 1}
                    },
                    {
                        "type": "sphere",
                        "name": "ball2",
                        "position": [5, 0.5, 0],
                        "params": {"radius": 0.5},
                        "physics": {"mass": 1, "velocity": [-5, 0, 0], "restitution": 1}
                    }
                ],
                "simulation": {
                    "gravity": [0, -9.81, 0],
                    "timeScale": 1.0
                }
            }
        },
        "projectile": {
            "name": "Projectile Motion",
            "description": "Ball launched at an angle",
            "config": {
                "objects": [
                    {
                        "type": "sphere",
                        "name": "ball",
                        "position": [0, 0.5, 0],
                        "params": {"radius": 0.5},
                        "physics": {"mass": 1, "velocity": [10.6, 10.6, 0]}
                    }
                ],
                "simulation": {
                    "gravity": [0, -9.81, 0],
                    "timeScale": 1.0
                }
            }
        }
    }
    
    return jsonify(templates)


@physics_bp.route("/api/physics/telemetry", methods=["POST"])
def log_telemetry():
    """
    Logs experiment execution telemetry for analysis.
    """
    try:
        data = request.get_json()
        telemetry_record = {
            'experiment_type': data.get('experiment_type', 'unknown'),
            'user_description': data.get('description', ''),
            'parameters_modified': data.get('parameters_modified', []),
            'execution_time': data.get('execution_time', 0),
            'created_at': datetime.datetime.utcnow().isoformat()
        }
        
        # Log locally as backup
        try:
            import os
            os.makedirs('data', exist_ok=True)
            with open('data/physics_telemetry.log', 'a', encoding='utf-8') as f:
                f.write(json.dumps(telemetry_record) + '\n')
        except Exception:
            pass
        
        return jsonify({"status": "ok"})
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
