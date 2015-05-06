import sys

def format_cols(cols):
    widths = [0] * len(cols[0])

    for i in cols:
        for idx, val in enumerate(i):
            widths[idx] = max(len(val), widths[idx])

    f = ""

    t = []
    for i in widths:
        t.append("%%-0%ds" % (i,))

    return "    ".join(t)

def column_report(title, fields, cols):
    l = []
    l.append("[" + title + "]")
    l.append("")


    f = format_cols([fields] + cols)

    header = f % tuple(fields)
    l.append(header)
    l.append("-" * len(header))
    for i in cols:
        l.append(f % tuple(i))

    l.append("")
    l.append("")
    return "\n".join(l)

def basename(uri):
    return uri.rstrip("/").split("/")[-1]

def step(desc):
    print desc
    print "=" * len(desc)
    print

def end_step():
    raw_input("Press enter to run the next step.")
    print
    print

def check_response(r, expected_statuses=None):
    if expected_statuses == None:
        expected_statuses = [200]

    ok = False

    for i in expected_statuses:
        if r.status_code == i:
            ok = True
            break

    if not ok:
        print "Request failed to succeed:"
        print "Status: %s" % (r.status_code,)
        print r.content
        sys.exit(1)
