import json

class NetworkModel:
    def __init__(self, routers, links, labels, atoms):
        self.routers = routers
        self.links = links
        self.labels = labels
        self.atoms = atoms

    def __repr__(self):
        return (f"NetworkModel(routers={len(self.routers)}, "
                f"links={len(self.links)}, labels={len(self.labels)}, atoms={len(self.atoms)})")


def load_network_model(file_path: str) -> NetworkModel:
    with open(file_path, 'r') as f:
        data = json.load(f)

    network = data.get("network", {})
    routers = [r["name"] for r in network.get("routers", []) if "name" in r]
    links = [{"from": l["from_router"], "to": l["to_router"]}
             for l in network.get("links", []) if "from_router" in l and "to_router" in l]

    labels = set()
    atoms = set()

    for router in network.get("routers", []):
        router_name = router["name"]
        for interface in router.get("interfaces", []):
            for label, entries in interface.get("routing_table", {}).items():
                labels.add(str(label))
                for entry in entries:
                    atoms.add(f"{router_name}#{entry['out']}")

    return NetworkModel(
        routers=sorted(routers),
        links=links,
        labels=sorted(labels, key=lambda x: (not x.isdigit(), x)),
        atoms=sorted(atoms)
    )




if __name__ == "__main__":
    
    model_path = "Aarnet_Gen_1.json" 
    network_model = load_network_model(f"networks/{model_path}")
    
    print("Routers:")
    for router in network_model.routers:
        print(f" - {router}")

    print("\nLinks:")
    for link in network_model.links:
        print(f" - {link['from']} -> {link['to']}")
    #routers_text = ", ".join(network_model.routers)
    #print(network_model.routers)
    print(network_model.labels)

