// GDS VoxelInteractor — dig (left click) and place (right click) blocks in a VoxelWorld from the camera centre.
// Keys 1-9 pick the block to place. Put it on the player camera. Works with the Input System or the legacy Input.
using UnityEngine;
#if GDS_INPUTSYSTEM && ENABLE_INPUT_SYSTEM
using UnityEngine.InputSystem;
#endif

namespace GDS
{
    public class VoxelInteractor : MonoBehaviour
    {
        public VoxelWorld world;
        public float reach = 6f;
        public Block placeBlock = Block.Planks;
        public Block[] hotbar = { Block.Planks, Block.Stone, Block.Dirt, Block.Brick, Block.Sand, Block.Wood, Block.Leaves, Block.Gravel, Block.Snow };
        public System.Action<Vector3Int, Block> OnDig, OnPlace;

        Camera cam;

        void Awake()
        {
            cam = GetComponent<Camera>(); if (cam == null) cam = Camera.main;
            if (world == null) world = FindAnyObjectByType<VoxelWorld>();
        }

        void Update()
        {
            if (world == null || cam == null) return;
            bool dig, place; int slot = -1;
#if GDS_INPUTSYSTEM && ENABLE_INPUT_SYSTEM
            var mouse = Mouse.current; var kb = Keyboard.current;
            dig = mouse != null && mouse.leftButton.wasPressedThisFrame;
            place = mouse != null && mouse.rightButton.wasPressedThisFrame;
            if (kb != null) for (int i = 0; i < 9; i++) if (kb[Key.Digit1 + i].wasPressedThisFrame) slot = i;
#else
            dig = Input.GetMouseButtonDown(0); place = Input.GetMouseButtonDown(1);
            for (int i = 0; i < 9; i++) if (Input.GetKeyDown(KeyCode.Alpha1 + i)) slot = i;
#endif
            if (slot >= 0 && slot < hotbar.Length) placeBlock = hotbar[slot];
            if (!dig && !place) return;
            var ray = cam.ViewportPointToRay(new Vector3(0.5f, 0.5f, 0));
            if (!world.RaycastBlock(ray, reach, out var hit, out var before)) return;
            if (dig)
            {
                var old = (Block)world.GetBlock(hit);
                if (world.SetBlock(hit, Block.Air)) OnDig?.Invoke(hit, old);
            }
            else
            {
                // never place inside the player
                var feet = world.transform.InverseTransformPoint(cam.transform.position);
                var p = Vector3Int.FloorToInt(feet);
                if (before == p || before == p + Vector3Int.down || before == p + Vector3Int.down * 2) return;
                if (world.SetBlock(before, placeBlock)) OnPlace?.Invoke(before, placeBlock);
            }
        }
    }
}
