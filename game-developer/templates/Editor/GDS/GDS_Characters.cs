// GDS Characters — rig + Animator setup from code for CC0 packs (KayKit, Kenney Animated Characters, Quaternius UAL/UBC, Mixamo FBX).
// Usage (execute_code):
//   return GDS.Characters.SetHumanoid("Assets/_Game/Art/Characters/knight.fbx");              // Humanoid rig so any UAL/Mixamo clip retargets
//   return GDS.Characters.SetHumanoidFolder("Assets/_Game/Art/Characters/UAL");                 // every FBX/GLB in the folder
//   return GDS.Characters.BuildController("Player", "Idle", "Walk", "Run", "Jump", "Attack"); // finds clips by name anywhere under Assets/_Game/Art
//   return GDS.Characters.MakePrefab("knight.fbx", "Assets/_Game/Animation/Player.controller", "char_player");
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEditor.Animations;
using UnityEngine;

namespace GDS
{
    public static class Characters
    {
        public const string AnimRoot = "Assets/_Game/Animation";
        public const string CharRoot = "Assets/_Game/Art/Characters";

        public static string SetHumanoid(string modelPath, bool loopAllClips = true)
        {
            if (!(AssetImporter.GetAtPath(modelPath) is ModelImporter mi)) return "{\"status\":\"FAIL\",\"error\":\"not a model importer\"}";
            mi.animationType = ModelImporterAnimationType.Human; mi.avatarSetup = ModelImporterAvatarSetup.CreateFromThisModel;
            if (loopAllClips)
            {
                var clips = mi.defaultClipAnimations;
                foreach (var c in clips) { c.loopTime = !(c.name.ToLowerInvariant().Contains("death") || c.name.ToLowerInvariant().Contains("die")); c.lockRootRotation = true; c.lockRootHeightY = true; c.keepOriginalPositionXZ = true; c.keepOriginalPositionY = true; c.lockRootPositionXZ = true; }
                mi.clipAnimations = clips;
            }
            mi.SaveAndReimport();
            var ok = mi.animationType == ModelImporterAnimationType.Human;
            return "{\"status\":\"" + (ok ? "PASS" : "FAIL") + "\",\"model\":\"" + Common.Esc(modelPath) + "\",\"clips\":" + mi.clipAnimations.Length + "}";
        }

        public static string SetHumanoidFolder(string folder)
        {
            int n = 0;
            foreach (var g in AssetDatabase.FindAssets("t:Model", new[] { folder })) { SetHumanoid(AssetDatabase.GUIDToAssetPath(g)); n++; }
            return "{\"status\":\"PASS\",\"models\":" + n + "}";
        }

        /// <summary>Animator Controller: Speed float drives Idle/Walk/Run blend tree; Jump/Attack/Hit/Death as triggers (only if a clip is found).</summary>
        public static string BuildController(string name, string idle, string walk, string run = null, string jump = null, string attack = null, string hit = null, string death = null, string searchRoot = Common.ArtRoot)
        {
            Common.EnsureFolder(AnimRoot);
            var path = $"{AnimRoot}/{name}.controller";
            var ctrl = AnimatorController.CreateAnimatorControllerAtPath(path);
            ctrl.AddParameter("Speed", AnimatorControllerParameterType.Float);
            ctrl.AddParameter("Grounded", AnimatorControllerParameterType.Bool);
            var sm = ctrl.layers[0].stateMachine;
            var missing = new List<string>();

            var loco = ctrl.CreateBlendTreeInController("Locomotion", out var tree);
            tree.blendParameter = "Speed"; tree.blendType = BlendTreeType.Simple1D; tree.useAutomaticThresholds = false;
            AddMotion(tree, idle, 0f, missing, searchRoot); AddMotion(tree, walk, 2f, missing, searchRoot);
            if (!string.IsNullOrEmpty(run)) AddMotion(tree, run, 5f, missing, searchRoot);
            sm.defaultState = loco;

            foreach (var (trig, clipName) in new[] { ("Jump", jump), ("Attack", attack), ("Hit", hit), ("Death", death) })
            {
                if (string.IsNullOrEmpty(clipName)) continue;
                var clip = FindClip(clipName, searchRoot);
                if (clip == null) { missing.Add(clipName); continue; }
                ctrl.AddParameter(trig, AnimatorControllerParameterType.Trigger);
                var st = sm.AddState(trig); st.motion = clip;
                var t = sm.AddAnyStateTransition(st); t.AddCondition(AnimatorConditionMode.If, 0, trig); t.duration = 0.1f; t.canTransitionToSelf = false;
                if (trig != "Death") { var back = st.AddTransition(loco); back.hasExitTime = true; back.exitTime = 0.9f; back.duration = 0.15f; }
            }
            AssetDatabase.SaveAssets();
            return "{\"status\":\"" + (missing.Contains(idle) || missing.Contains(walk) ? "FAIL" : "PASS") + "\",\"controller\":\"" + path + "\",\"missingClips\":[\"" + string.Join("\",\"", missing) + "\"]}";
        }

        public static string MakePrefab(string modelFileOrPath, string controllerPath, string prefabName, bool addCharacterController = true)
        {
            var model = Common.LoadModel(modelFileOrPath, Common.ArtRoot);
            if (model == null) return "{\"status\":\"FAIL\",\"error\":\"model not found\"}";
            var inst = (GameObject)PrefabUtility.InstantiatePrefab(model);
            inst.name = prefabName;
            var anim = inst.GetComponent<Animator>(); if (anim == null) anim = inst.AddComponent<Animator>();
            var ctrl = AssetDatabase.LoadAssetAtPath<RuntimeAnimatorController>(controllerPath);
            if (ctrl != null) anim.runtimeAnimatorController = ctrl;
            anim.applyRootMotion = false;
            if (addCharacterController && inst.GetComponent<CharacterController>() == null)
            {
                var cc = inst.AddComponent<CharacterController>();
                float h = Common.TryGetBounds(inst, out var b) ? b.size.y : 1.8f;
                cc.height = h; cc.radius = Mathf.Clamp(h * 0.22f, 0.25f, 0.5f); cc.center = new Vector3(0, h / 2f, 0); cc.stepOffset = 0.3f; cc.slopeLimit = 45f;
            }
            Common.EnsureFolder(Common.PrefabsRoot);
            var path = $"{Common.PrefabsRoot}/{prefabName}.prefab";
            var prefab = PrefabUtility.SaveAsPrefabAssetAndConnect(inst, path, InteractionMode.AutomatedAction);
            return "{\"status\":\"PASS\",\"prefab\":\"" + path + "\"}";
        }

        public static AnimationClip FindClip(string nameContains, string root)
        {
            var exact = new List<AnimationClip>(); var partial = new List<AnimationClip>();
            foreach (var g in AssetDatabase.FindAssets("t:AnimationClip", new[] { root }))
            {
                var p = AssetDatabase.GUIDToAssetPath(g);
                foreach (var a in AssetDatabase.LoadAllAssetRepresentationsAtPath(p).OfType<AnimationClip>().Concat(new[] { AssetDatabase.LoadAssetAtPath<AnimationClip>(p) }))
                {
                    if (a == null || a.name.StartsWith("__preview")) continue;
                    if (string.Equals(a.name, nameContains, StringComparison.OrdinalIgnoreCase)) exact.Add(a);
                    else if (a.name.IndexOf(nameContains, StringComparison.OrdinalIgnoreCase) >= 0) partial.Add(a);
                }
            }
            return exact.FirstOrDefault() ?? partial.OrderBy(c => c.name.Length).FirstOrDefault();
        }

        static void AddMotion(BlendTree tree, string clipName, float threshold, List<string> missing, string root)
        {
            var c = FindClip(clipName, root);
            if (c == null) { missing.Add(clipName); return; }
            tree.AddChild(c, threshold);
        }

        public static string ListClips(string root = Common.ArtRoot)
        {
            var names = new SortedSet<string>();
            foreach (var g in AssetDatabase.FindAssets("t:AnimationClip", new[] { root }))
                foreach (var a in AssetDatabase.LoadAllAssetRepresentationsAtPath(AssetDatabase.GUIDToAssetPath(g)).OfType<AnimationClip>()) if (!a.name.StartsWith("__preview")) names.Add(a.name);
            return "[\"" + string.Join("\",\"", names) + "\"]";
        }
    }
}
