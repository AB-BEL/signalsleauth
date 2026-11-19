/** Legacy offline Chapter 1 data — mobile Play now loads /api/chapter/:n/game-package dynamically. */
/** Chapter 1 — 7 levels, same as web play_chapter1.html / question bank */
export const CHAPTER1_LEVELS = [
  {
    "id": 1,
    "title": "The Nature of a Signal",
    "maxScore": 30,
    "brief": "A junior analyst mixed up fundamental definitions. Restore the correct conceptual foundation.",
    "clues": [
      "“The term signal is generally applied to something that conveys information.”",
      "Continuous-time vs discrete-time vs digital signals.",
      "Focus is discrete-time signals and systems, not only finite-precision digital."
    ],
    "questions": [
      {
        "text": "What essential property makes something a signal?",
        "points": 10,
        "keys": [
          {
            "phrases": [
              "conveys information",
              "convey information",
              "carries information",
              "contains information"
            ],
            "weight": 6,
            "label": "conveys information"
          },
          {
            "phrases": [
              "pattern of variations",
              "variations",
              "varies"
            ],
            "weight": 4,
            "label": "pattern of variations"
          }
        ],
        "model": "A signal conveys information, contained in a pattern of variations."
      },
      {
        "text": "Distinguish continuous-time, discrete-time, and digital signals.",
        "points": 12,
        "keys": [
          {
            "phrases": [
              "continuous-time",
              "continuous time",
              "analog",
              "continuum"
            ],
            "weight": 3,
            "label": "continuous-time"
          },
          {
            "phrases": [
              "discrete-time",
              "discrete time",
              "sequence"
            ],
            "weight": 4,
            "label": "discrete-time"
          },
          {
            "phrases": [
              "digital",
              "amplitude",
              "quantized",
              "finite precision",
              "both time and amplitude"
            ],
            "weight": 5,
            "label": "digital"
          }
        ],
        "model": "Continuous-time: continuous independent variable. Discrete-time: sequence at discrete instants. Digital: time and amplitude discrete."
      },
      {
        "text": "Why emphasize discrete-time rather than only digital processing?",
        "points": 8,
        "keys": [
          {
            "phrases": [
              "more general",
              "general framework",
              "includes digital",
              "special case",
              "discrete-time"
            ],
            "weight": 4,
            "label": "more general"
          },
          {
            "phrases": [
              "high-precision",
              "fine quantization",
              "valid for digital"
            ],
            "weight": 4,
            "label": "valid for digital"
          }
        ],
        "model": "Discrete-time theory is more general and remains valid for digital implementations."
      }
    ]
  },
  {
    "id": 2,
    "title": "The Great Shift",
    "maxScore": 30,
    "brief": "Reconstruct the shift from analog to discrete-time / digital signal processing.",
    "clues": [
      "Before the 1960s, processing was almost exclusively continuous-time analog.",
      "Digital computers, microprocessors, A/D–D/A, and the FFT drove the shift.",
      "Early computers often simulated analog systems offline."
    ],
    "questions": [
      {
        "text": "Dominant technology before the 1960s?",
        "points": 8,
        "keys": [
          {
            "phrases": [
              "analog",
              "continuous-time",
              "continuous time"
            ],
            "weight": 8,
            "label": "analog/continuous-time"
          }
        ],
        "model": "Continuous-time analog technology."
      },
      {
        "text": "Name three enabling factors for the shift.",
        "points": 12,
        "keys": [
          {
            "phrases": [
              "computer",
              "microprocessor"
            ],
            "weight": 3,
            "label": "computers"
          },
          {
            "phrases": [
              "a/d",
              "d/a",
              "converter",
              "conversion"
            ],
            "weight": 3,
            "label": "A/D D/A"
          },
          {
            "phrases": [
              "fft",
              "fast fourier",
              "parametric",
              "multirate",
              "polyphase",
              "wavelet"
            ],
            "weight": 3,
            "label": "FFT/theory"
          },
          {
            "phrases": [
              "three",
              "3"
            ],
            "weight": 3,
            "label": "multiple factors"
          }
        ],
        "model": "Computers/microprocessors; A/D & D/A; FFT and related theory."
      },
      {
        "text": "Why were early computers seen as simulators of analog systems?",
        "points": 10,
        "keys": [
          {
            "phrases": [
              "slow",
              "expensive",
              "not real-time",
              "non-real-time",
              "offline"
            ],
            "weight": 5,
            "label": "limits"
          },
          {
            "phrases": [
              "simulate",
              "approximation",
              "approximate",
              "analog"
            ],
            "weight": 5,
            "label": "simulate analog"
          }
        ],
        "model": "Expensive/slow; used offline to simulate analog systems."
      }
    ]
  },
  {
    "id": 3,
    "title": "The FFT Revelation",
    "maxScore": 32,
    "brief": "Identify the 1965 discovery that changed the economics of signal processing.",
    "clues": [
      "Cooley and Tukey (1965) disclosed the FFT.",
      "FFT is inherently discrete-time, not an approximation of continuous-time.",
      "Helped establish discrete-time SP as a field in its own right."
    ],
    "questions": [
      {
        "text": "Who published the modern FFT and in what year?",
        "points": 10,
        "keys": [
          {
            "phrases": [
              "cooley",
              "tukey"
            ],
            "weight": 6,
            "label": "Cooley & Tukey"
          },
          {
            "phrases": [
              "1965"
            ],
            "weight": 4,
            "label": "1965"
          }
        ],
        "model": "Cooley and Tukey, 1965."
      },
      {
        "text": "What conceptual shift did the FFT help trigger?",
        "points": 12,
        "keys": [
          {
            "phrases": [
              "discrete-time",
              "exact",
              "independent field",
              "in its own right",
              "reformulation"
            ],
            "weight": 6,
            "label": "discrete-time field"
          },
          {
            "phrases": [
              "practical",
              "interactive",
              "experimentation"
            ],
            "weight": 4,
            "label": "practical use"
          }
        ],
        "model": "Reformulation in exact discrete-time mathematics; field in its own right."
      },
      {
        "text": "Why is the FFT inherently discrete-time significant?",
        "points": 10,
        "keys": [
          {
            "phrases": [
              "exact",
              "not an approximation",
              "not approximation",
              "stands on its own"
            ],
            "weight": 6,
            "label": "exact DT"
          },
          {
            "phrases": [
              "sequence",
              "discrete-time signal"
            ],
            "weight": 4,
            "label": "on sequences"
          }
        ],
        "model": "Yields exact discrete-time relationships, not a continuous-time approximation."
      }
    ]
  },
  {
    "id": 4,
    "title": "Real-Time vs Stored Processing",
    "maxScore": 30,
    "brief": "Settle whether every useful DSP system must run in real time.",
    "clues": [
      "CD and MP3 are asymmetric: process once, store, play back in real time.",
      "Seismic processing was often non-real-time yet highly valuable."
    ],
    "questions": [
      {
        "text": "Define asymmetric processing (CD/MP3).",
        "points": 10,
        "keys": [
          {
            "phrases": [
              "once",
              "processed once",
              "offline",
              "stored",
              "store"
            ],
            "weight": 5,
            "label": "process once/store"
          },
          {
            "phrases": [
              "playback",
              "reconstruct",
              "real time",
              "real-time",
              "later"
            ],
            "weight": 5,
            "label": "later playback"
          }
        ],
        "model": "Process once, store, reconstruct in real time later."
      },
      {
        "text": "Historical non-real-time example?",
        "points": 10,
        "keys": [
          {
            "phrases": [
              "seismic",
              "geophysical",
              "geophysic",
              "exploration"
            ],
            "weight": 8,
            "label": "seismic"
          },
          {
            "phrases": [
              "offline",
              "hours",
              "non-real-time"
            ],
            "weight": 2,
            "label": "offline"
          }
        ],
        "model": "Seismic/geophysical exploration processed offline."
      },
      {
        "text": "Why was non-real-time digital still a major advance?",
        "points": 10,
        "keys": [
          {
            "phrases": [
              "flexibility",
              "flexible",
              "change",
              "adjust"
            ],
            "weight": 5,
            "label": "flexibility"
          },
          {
            "phrases": [
              "hardware",
              "analog",
              "economic",
              "payoff"
            ],
            "weight": 5,
            "label": "avoid hardware cost"
          }
        ],
        "model": "Flexibility without building new analog hardware."
      }
    ]
  },
  {
    "id": 5,
    "title": "Why Fundamentals Still Matter",
    "maxScore": 30,
    "brief": "Explain why theory still matters when software libraries exist.",
    "clues": [
      "Understand what is computed and how to interpret results.",
      "Properties like convolution↔multiplication enable smart tools."
    ],
    "questions": [
      {
        "text": "What must users still understand with high-level software?",
        "points": 10,
        "keys": [
          {
            "phrases": [
              "what is computed",
              "interpret",
              "interpretation",
              "how the result"
            ],
            "weight": 6,
            "label": "interpret results"
          },
          {
            "phrases": [
              "concepts",
              "theorems",
              "properties",
              "fundamentals",
              "theory"
            ],
            "weight": 4,
            "label": "concepts"
          }
        ],
        "model": "What is computed and how to interpret results; underlying concepts."
      },
      {
        "text": "Example property enabling automatic alternative implementations?",
        "points": 12,
        "keys": [
          {
            "phrases": [
              "convolution",
              "multiplication",
              "frequency domain"
            ],
            "weight": 6,
            "label": "conv↔mult"
          },
          {
            "phrases": [
              "sampling",
              "aliasing",
              "decimation",
              "interpolation"
            ],
            "weight": 6,
            "label": "sampling/aliasing"
          }
        ],
        "model": "Convolution↔multiplication or sampling rate↔aliasing."
      },
      {
        "text": "Meaning of “uncover rather than cover” a subject?",
        "points": 8,
        "keys": [
          {
            "phrases": [
              "uncover",
              "explore",
              "open up",
              "variety",
              "further"
            ],
            "weight": 5,
            "label": "explore"
          },
          {
            "phrases": [
              "not exhaust",
              "not list every",
              "rather than cover"
            ],
            "weight": 3,
            "label": "not exhaustive"
          }
        ],
        "model": "Open rich theory/applications rather than list every topic."
      }
    ]
  },
  {
    "id": 6,
    "title": "Applications That Shaped the Field",
    "maxScore": 30,
    "brief": "Map early drivers and modern application domains.",
    "clues": [
      "Early: seismology, radar, communications, speech.",
      "Modern: multimedia, finance, medical imaging, DNA, MEMS."
    ],
    "questions": [
      {
        "text": "Three early application domains?",
        "points": 10,
        "keys": [
          {
            "phrases": [
              "seismic",
              "seismology",
              "geophysic"
            ],
            "weight": 3,
            "label": "seismic"
          },
          {
            "phrases": [
              "radar"
            ],
            "weight": 3,
            "label": "radar"
          },
          {
            "phrases": [
              "communication",
              "speech",
              "vocoder"
            ],
            "weight": 3,
            "label": "comms/speech"
          }
        ],
        "model": "Seismology, radar, communications/speech."
      },
      {
        "text": "Three contemporary/emerging areas?",
        "points": 10,
        "keys": [
          {
            "phrases": [
              "video",
              "audio",
              "multimedia",
              "mpeg",
              "jpeg",
              "phone"
            ],
            "weight": 3,
            "label": "multimedia"
          },
          {
            "phrases": [
              "finance",
              "financial",
              "economic"
            ],
            "weight": 3,
            "label": "finance"
          },
          {
            "phrases": [
              "medical",
              "imaging",
              "dna",
              "mems",
              "sensor"
            ],
            "weight": 3,
            "label": "medical/DNA/MEMS"
          }
        ],
        "model": "Multimedia, financial engineering, medical/DNA/MEMS."
      },
      {
        "text": "How do new applications borrow and stimulate new algorithms?",
        "points": 10,
        "keys": [
          {
            "phrases": [
              "adapt",
              "borrow",
              "existing"
            ],
            "weight": 4,
            "label": "borrow"
          },
          {
            "phrases": [
              "stimulate",
              "new algorithm",
              "invent",
              "drive new"
            ],
            "weight": 4,
            "label": "new algorithms"
          },
          {
            "phrases": [
              "two-way",
              "interaction"
            ],
            "weight": 2,
            "label": "two-way"
          }
        ],
        "model": "Adapt existing knowledge; new needs stimulate new algorithms."
      }
    ]
  },
  {
    "id": 7,
    "title": "The Unfinished Story – Synthesis",
    "maxScore": 28,
    "brief": "Why does grounding in discrete-time fundamentals remain indispensable?",
    "clues": [
      "Hardware waves change what is practical; mathematics stays central.",
      "Theory must be ready before hardware makes algorithms viable.",
      "New domains keep appearing."
    ],
    "questions": [
      {
        "text": "Why are fundamentals still indispensable? (use ≥3 ideas from the chapter)",
        "points": 20,
        "keys": [
          {
            "phrases": [
              "stable",
              "core",
              "mathematics",
              "fundamentals",
              "underlying"
            ],
            "weight": 4,
            "label": "math core"
          },
          {
            "phrases": [
              "hardware",
              "impractical",
              "viable",
              "ready"
            ],
            "weight": 4,
            "label": "hardware lag"
          },
          {
            "phrases": [
              "interpret",
              "interpretation",
              "properties"
            ],
            "weight": 4,
            "label": "interpretation"
          },
          {
            "phrases": [
              "new application",
              "emerging",
              "future",
              "contribute"
            ],
            "weight": 4,
            "label": "new apps"
          },
          {
            "phrases": [
              "software",
              "library",
              "not enough"
            ],
            "weight": 4,
            "label": "software limits"
          }
        ],
        "model": "Fundamentals are the stable core; theory precedes hardware; interpretation and new apps still need deep knowledge."
      },
      {
        "text": "Most memorable guiding principle from Ch.1 and why?",
        "points": 8,
        "keys": [
          {
            "phrases": [
              "uncover",
              "cover",
              "fundamental",
              "principle",
              "because",
              "important"
            ],
            "weight": 5,
            "label": "principle+reason"
          },
          {
            "phrases": [
              "fft",
              "discrete-time",
              "field",
              "flexibility"
            ],
            "weight": 3,
            "label": "concrete idea"
          }
        ],
        "model": "Any thoughtful principle with a clear reason."
      }
    ]
  }
];

export function normalize(s) {
  return (s || '').toLowerCase().replace(/[^\w\s]/g, ' ').replace(/\s+/g, ' ').trim()
}

export function evaluateAnswer(text, q) {
  const norm = normalize(text)
  if (!norm || norm.length < 3) {
    return { score: 0, max: q.points, matched: [], missing: (q.keys || []).map((k) => k.label), ratio: 0 }
  }
  let ew = 0, tw = 0
  const matched = [], missing = []
  ;(q.keys || []).forEach((k) => {
    tw += k.weight
    if ((k.phrases || []).some((ph) => norm.includes(normalize(ph)))) {
      ew += k.weight
      matched.push(k.label)
    } else missing.push(k.label)
  })
  const ratio = tw ? ew / tw : 0
  let score = Math.round(ratio * q.points)
  if (score === 0 && norm.length > 40) score = Math.min(2, q.points)
  return { score, max: q.points, matched, missing, ratio }
}
