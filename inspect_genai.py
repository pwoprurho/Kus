from google.genai import types

if hasattr(types, 'Part'):
    print("Attributes of types.Part:")
    # print([d for d in dir(types.Part) if not d.startswith('_')])
    # Just print the __annotations__ if available to see types
    if hasattr(types.Part, '__annotations__'):
        print(types.Part.__annotations__)
else:
    print("types.Part not found.")

