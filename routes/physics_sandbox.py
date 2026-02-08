# routes/physics_sandbox.py
"""
Physics Sandbox API Routes
Handles experiment generation, validation, and execution.
"""

import json
import re
from flask import Blueprint, request, jsonify, render_template
from core.stem_ai import StemAIEngine
from core.validator import PhysicsCodeValidator
from core.security import sign_forensic_trace
import datetime

physics_bp = Blueprint('physics', __name__)

# Initialize components
validator = PhysicsCodeValidator()
stem_engine = StemAIEngine()

# In-memory session store (In production, use Redis/Database)
sessions = {}

@physics_bp.route("/physics-sandbox")
def physics_sandbox_view():
    """Renders the Conversational STEM Sandbox interface."""
    return render_template('physics_sandbox.html')


@physics_bp.route("/api/stem/chat", methods=["POST"])
def stem_chat():
    """
    Handles conversational detail gathering.
    """
    try:
        data = request.get_json()
        message = data.get('message', '').strip()
        session_id = data.get('session_id', 'default')
        
        if not message:
            return jsonify({"error": "No message provided"}), 400
            
        # Get or create session context
        session = sessions.get(session_id, {"history": [], "design": ""})
        
        # Interact with the AI
        result = stem_engine.chat_interact(message, context_logs=session["history"])
        
        # Update history
        session["history"].append({"role": "user", "content": message})
        session["history"].append({"role": "assistant", "content": result["response"]})
        
        # Save session
        sessions[session_id] = session
        
        return jsonify({
            "success": True,
            "response": result["response"],
            "state": result["state"],
            "thought_trace": result["thought_trace"]
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@physics_bp.route("/api/stem/generate", methods=["POST"])
def generate_stem_experiment():
    """
    Triggers the high-fidelity code generation phase using Gemini 3.0.
    """
    try:
        data = request.get_json()
        design_doc = data.get('design', '').strip()
        session_id = data.get('session_id', 'default')
        
        if not design_doc:
            # If no design doc provided, try to compile from session history
            session = sessions.get(session_id)
            if session:
                design_doc = "\n".join([f"{h['role']}: {h['content']}" for h in session["history"]])
            else:
                return jsonify({"error": "No design context found"}), 400
        
        # Generate simulation
        result = stem_engine.generate_simulation(design_doc)
        
        if result.get('errors'):
            return jsonify({
                "success": False,
                "error": "Generation failed",
                "details": result['errors']
            }), 500
            
        # Validate code
        code = result.get('threejs_code', '')
        validation = validator.validate(code)
        
        if not validation['valid']:
            return jsonify({
                "success": False,
                "error": "Security validation failed",
                "issues": validation['issues']
            }), 500
            
        return jsonify({
            "success": True,
            "experiment": result,
            "thought_trace": result.get("thought_trace")
        })
        
    except Exception as e:
        import traceback
        print(f"CRITICAL [STEM] Generation Endpoint Error: {str(e)}")
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


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
