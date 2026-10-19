using System;
using System.Collections.Generic;
namespace UnityEngine.InputSystem {
  public enum Key { None, I, Escape, F, F1, F2, F3, F4, F5, F6, F7, F8, F9, F10, F11 }
  public class ButtonControl { public bool wasPressedThisFrame; public bool isPressed; public bool wasReleasedThisFrame; }
  public class Keyboard { public static Keyboard current; public ButtonControl this[Key k] => new ButtonControl();
    public ButtonControl f1Key,f2Key,f3Key,f4Key,f5Key,f6Key,f7Key,f8Key,f9Key,f10Key,pageUpKey,pageDownKey; }
  public class Mouse { public static Mouse current; public Vector2Control scroll; }
  public class Vector2Control { public Vector2 ReadValue() => default; }
  public class InputBinding { public string path; public string effectivePath; public bool isComposite; public bool isPartOfComposite; public string name; public string groups; public string overridePath; }
  public class InputActionMap { public bool enabled; public string name; public IReadOnlyList<InputAction> actions; public InputAction FindAction(string n, bool t=false)=>null; public void Enable(){} public void Disable(){} }
  public class InputAction { public string name; public InputActionMap actionMap; public IReadOnlyList<InputBinding> bindings;
    public T ReadValue<T>() where T: struct => default; public bool WasPressedThisFrame()=>false; public bool IsPressed()=>false; public bool WasReleasedThisFrame()=>false;
    public string GetBindingDisplayString(int i=0, int o=0)=>""; public object AddBinding(string p)=>null; public object ApplyBindingOverride(int i,string p)=>null; public void RemoveBindingOverride(int i){} public object ApplyBindingOverride(string p)=>null; }
  public class InputActionAsset : ScriptableObject { public InputActionMap FindActionMap(string n, bool t=false)=>null; public void RemoveAllBindingOverrides(){} public string SaveBindingOverridesAsJson()=>""; public void LoadBindingOverridesFromJson(string j, bool r=true){} }
  public static class InputActionRebindingExtensions { public class RebindingOperation { public void Cancel(){} public RebindingOperation WithControlsExcluding(string s)=>this; public RebindingOperation WithCancelingThrough(string s)=>this; public RebindingOperation OnComplete(Action<RebindingOperation> a)=>this; public RebindingOperation OnCancel(Action<RebindingOperation> a)=>this; public RebindingOperation Start()=>this; public void Dispose(){} public RebindingOperation WithTargetBinding(int i)=>this; public RebindingOperation WithMatchingEventsBeingSuppressed(bool b=true)=>this; public RebindingOperation OnMatchWaitForAnother(float f)=>this; public RebindingOperation WithControlsHavingToMatchPath(string s)=>this; public RebindingOperation WithExpectedControlType(string s)=>this; public RebindingOperation WithBindingGroup(string s)=>this; public RebindingOperation OnPotentialMatch(Action<RebindingOperation> a)=>this; }
    public static RebindingOperation PerformInteractiveRebinding(this InputAction a,int i=-1)=>null; }
}
namespace UnityEngine.UIElements {
  [AttributeUsage(AttributeTargets.All)] public class UxmlElementAttribute : Attribute { public UxmlElementAttribute(){} public UxmlElementAttribute(string n){} }
  [AttributeUsage(AttributeTargets.All)] public class UxmlAttributeAttribute : Attribute { public UxmlAttributeAttribute(){} public UxmlAttributeAttribute(string n){} }
}
namespace UnityEngine.Rendering { public class Volume : MonoBehaviour { public float weight; } }
