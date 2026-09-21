using NUnit.Framework;
using UnityEngine;

public class PlayerMovementTests
{
    [Test]
    public void Move_IncreasesX()
    {
        var go = new GameObject("Player");
        var pc = go.AddComponent<PlayerController>();
        var start = go.transform.position;
        pc.SetMove(Vector2.right);
        pc.Step(0.5f);
        Assert.Greater(go.transform.position.x, start.x);
        Object.DestroyImmediate(go);
    }

    [Test]
    public void Move_ZeroKeepsPosition()
    {
        var go = new GameObject("Player");
        var pc = go.AddComponent<PlayerController>();
        var start = go.transform.position;
        pc.SetMove(Vector2.zero);
        pc.Step(0.5f);
        Assert.AreEqual(start.x, go.transform.position.x, 0.0001f);
        Object.DestroyImmediate(go);
    }
}
