export function element(id) {
    const result = document.getElementById(id);
    if (!result)
        throw new Error(`Missing application element: ${id}`);
    return result;
}
//# sourceMappingURL=dom.js.map