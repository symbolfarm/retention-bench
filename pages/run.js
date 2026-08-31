const steps = [
  {
    label:"Set-up", title:"One task, three independent arms",
    copy:"The harness will play the same six-instance toy schedule three times. Every arm begins with a fresh empty survive-directory; only its reset policy changes.",
    visual:`<span class="token">P<br><small>wipe</small></span><span class="token">C<br><small>no reset</small></span><span class="token">R(1)<br><small>keep disk</small></span>`,
    note:"This isolation is why the arms can be compared. P is not run before C in the same state directory.", state:{p:null,c:null,r:null,k:0,disk:"empty"}
  },
  {
    label:"Prior arm P", title:"What can the cold system do?",
    copy:"The prior arm sees a fresh process and wipes durable SUT state at each boundary. In this toy schedule it answers one of two scored probes correctly: P = 1/2.",
    visual:`<span class="process">fresh SUT</span><span class="arrow">→</span><span class="token">✓</span><span class="token">×</span>`,
    note:"P measures this system's stateless floor. It is not necessarily the task's analytic chance level.", state:{p:.5,c:null,r:null,k:0,disk:"wiped"}
  },
  {
    label:"Ceiling arm C", title:"What can it learn without interruption?",
    copy:"A separate no-reset process receives the teaching instances, keeps working state unbroken, and answers both scored probes correctly: C = 2/2.",
    visual:`<span class="token">norb</span><span class="arrow">→</span><span class="token">red</span><span class="arrow">→</span><span class="token">bin-a</span>`,
    note:"C is this SUT's measured learning ceiling on this schedule—not a universal maximum and not assumed to be 1.", state:{p:.5,c:1,r:null,k:0,disk:"separate arm"}
  },
  {
    label:"Retention arm R", title:"Teach, then persist before replying",
    copy:"The retention arm learns the associations. Before writing its reply, the SUT flushes the state it wants to retain into the survive-directory.",
    visual:`<span class="process">process A</span><span class="arrow">→</span><span class="disk">state.json<br><small>norb → red</small></span>`,
    note:"Flush-before-reply matters because the SUT receives no warning before SIGKILL. A clean-shutdown hook cannot save it.", state:{p:.5,c:1,r:null,k:0,disk:"1 file"}
  },
  {
    label:"Completion boundary", title:"Observe the completed instance",
    copy:"The harness ignores intermediate observations. After a complete instance it increments the 1-based ordinal, measures the survive-directory, and checks whether a next query exists and the schedule fires.",
    visual:`<span class="token">instance complete</span><span class="arrow">→</span><span class="token">ordinal 4</span><span class="arrow">→</span><span class="token">reset? yes</span>`,
    note:"The final run boundary is never counted as a scheduled reset because there is no next query for it to affect.", state:{p:.5,c:1,r:null,k:0,disk:"1 file · measured"}
  },
  {
    label:"Hard RESET", title:"Kill process A; keep only the directory",
    copy:"The harness sends SIGKILL to the SUT's process group and drops the handle. There is no graceful flush and no in-memory carry-over.",
    visual:`<span class="process killed">process A</span><span class="arrow">×</span><span class="disk">state.json<br><small>survives</small></span>`,
    note:"A hard reset is mechanical, not a request that the SUT promises to honour. This arm is non-wiping, so its on-disk artifact remains.", state:{p:.5,c:1,r:null,k:1,disk:"1 file · survives"}
  },
  {
    label:"Lazy respawn", title:"The next query creates process B",
    copy:"No replacement process is started during the reset itself. When the next query arrives, respond() lazily spawns a fresh process in the same survive-directory.",
    visual:`<span class="disk">state.json</span><span class="arrow">→</span><span class="process">process B</span>`,
    note:"Process B can re-read the artifact. It cannot recover process A's context, objects, caches, or unflushed state.", state:{p:.5,c:1,r:null,k:1,disk:"read by B"}
  },
  {
    label:"Post-reset probes", title:"What is still visible after disruption?",
    copy:"Process B answers both scored probes correctly from the surviving artifact, so this toy retention arm has R(1) = 2/2.",
    visual:`<span class="process">process B</span><span class="arrow">→</span><span class="token">✓ recall</span><span class="token">✓ transfer</span>`,
    note:"This shows capability survived the process reset. On its own it does not prove the state is an integrated abstraction rather than a recording.", state:{p:.5,c:1,r:1,k:1,disk:"1 file"}
  },
  {
    label:"Normalise", title:"Ask how much learnable improvement survived",
    copy:"The learnable band is C − P = 1 − 0.5 = 0.5. The retained improvement is R − P = 1 − 0.5 = 0.5. Their ratio is 1.0.",
    visual:`<span class="token">R − P<br><strong>0.5</strong></span><span class="arrow">÷</span><span class="token">C − P<br><strong>0.5</strong></span><span class="arrow">=</span><span class="token">1.0</span>`,
    note:"Read this as “all of what this system could learn was still visible after one reset,” not “the system has perfect memory in general.” The real implementation divides by max(C − P, ε) and excludes the point outright when the band falls below ε; this toy band of 0.5 is far above it.", state:{p:.5,c:1,r:1,k:1,disk:"1 file"}
  },
  {
    label:"Interpret", title:"Now choose the claim you actually want to test",
    copy:"A uniform sequence of resets would test graceful degradation. A single reset after learning with the episodic store removed would test migration into a durable artifact. The same k does not make those the same experiment.",
    visual:`<span class="token">uniform<br><small>degradation</small></span><span class="token">phased<br><small>migration</small></span>`,
    note:"Always report schedule placement alongside measured k. Reset count alone does not identify the experiment.", state:{p:.5,c:1,r:1,k:1,disk:"1 file"}
  }
];

let index = 0;
const $ = selector => document.querySelector(selector);
const progress = $("#progress");
steps.forEach(() => progress.append(document.createElement("span")));

function score(value) { return value == null ? "—" : value.toFixed(2); }
function render() {
  const step = steps[index];
  $("#step-label").textContent = `${step.label} · ${index + 1} of ${steps.length}`;
  $("#step-title").textContent = step.title;
  $("#step-copy").textContent = step.copy;
  $("#event-visual").innerHTML = step.visual;
  $("#step-note").textContent = step.note;
  [...progress.children].forEach((bar, i) => bar.classList.toggle("done", i <= index));
  $("#prev").disabled = index === 0;
  $("#next").disabled = index === steps.length - 1;
  $("#next").textContent = index === steps.length - 2 ? "Finish →" : "Next →";
  const s = step.state;
  $("#p-value").textContent = score(s.p);
  $("#c-value").textContent = score(s.c);
  $("#r-value").textContent = score(s.r);
  $("#k-value").textContent = s.k;
  $("#disk-value").textContent = s.disk;
  if (s.p != null && s.c != null && s.r != null) {
    const band = s.c - s.p;
    const norm = (s.r - s.p) / band;
    $("#norm-value").textContent = norm.toFixed(2);
    $("#ledger-note").textContent = `Learnable band: ${band.toFixed(2)}. Retained improvement: ${(s.r-s.p).toFixed(2)}.`;
  } else {
    $("#norm-value").textContent = "waiting…";
    $("#ledger-note").textContent = "Advance the run to fill the measured floor, ceiling, and retained arm.";
  }
}
$("#prev").addEventListener("click", () => { if (index > 0) { index--; render(); } });
$("#next").addEventListener("click", () => { if (index < steps.length - 1) { index++; render(); } });
$("#restart").addEventListener("click", () => { index = 0; render(); });
document.addEventListener("keydown", event => {
  if (event.key === "ArrowRight" && index < steps.length - 1) { index++; render(); }
  if (event.key === "ArrowLeft" && index > 0) { index--; render(); }
});
render();
