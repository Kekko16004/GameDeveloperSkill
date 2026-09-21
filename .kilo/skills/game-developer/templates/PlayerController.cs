using UnityEngine;
using UnityEngine.InputSystem;

[RequireComponent(typeof(CharacterController))]
public class PlayerController : MonoBehaviour
{
    public float moveSpeed = 6f;
    public float gravity = -24f;

    CharacterController _cc;
    Vector2 _move;
    float _vy;

    void Awake()
    {
        _cc = GetComponent<CharacterController>();
    }

    public void OnMove(InputAction.CallbackContext ctx)
    {
        _move = ctx.ReadValue<Vector2>();
    }

    public void SetMove(Vector2 value)
    {
        _move = value;
    }

    public Vector3 Step(float dt)
    {
        var planar = new Vector3(_move.x, 0f, _move.y);
        if (planar.sqrMagnitude > 1f) planar.Normalize();
        planar *= moveSpeed;

        if (_cc != null && _cc.isGrounded && _vy < 0f) _vy = -1f;
        _vy += gravity * dt;

        var delta = new Vector3(planar.x, _vy, planar.z) * dt;
        if (_cc != null) _cc.Move(delta);
        else transform.position += delta;
        return transform.position;
    }

    void Update()
    {
        Step(Time.deltaTime);
    }
}
