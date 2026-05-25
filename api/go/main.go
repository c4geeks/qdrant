// Package main demonstrates the official Qdrant Go client against a real cluster.
//
// Build:
//
//	go mod init qdrant-go-demo
//	go get github.com/qdrant/go-client/qdrant@latest
//	go run go_client.go
package main

import (
	"context"
	"fmt"
	"math/rand"
	"time"

	"github.com/qdrant/go-client/qdrant"
)

const (
	host       = "localhost"
	grpcPort   = 6334
	apiKey     = "PUT_YOUR_KEY_HERE"
	collection = "go_demo"
)

func main() {
	ctx, cancel := context.WithTimeout(context.Background(), 15*time.Second)
	defer cancel()

	client, err := qdrant.NewClient(&qdrant.Config{
		Host:   host,
		Port:   grpcPort,
		APIKey: apiKey,
		UseTLS: false,
	})
	must(err)
	defer client.Close()

	// 1. List collections
	cols, err := client.ListCollections(ctx)
	must(err)
	fmt.Println("=== Go: existing collections ===")
	for _, c := range cols {
		fmt.Println("  -", c)
	}

	// 2. Create the demo collection (drop first if it exists)
	_ = client.DeleteCollection(ctx, collection)
	must(client.CreateCollection(ctx, &qdrant.CreateCollection{
		CollectionName: collection,
		VectorsConfig: qdrant.NewVectorsConfig(&qdrant.VectorParams{
			Size:     8,
			Distance: qdrant.Distance_Cosine,
		}),
	}))
	fmt.Println("\n=== Go: created", collection, "===")

	// 3. Upsert 5 points
	rng := rand.New(rand.NewSource(42))
	points := make([]*qdrant.PointStruct, 5)
	for i := range points {
		vec := make([]float32, 8)
		for j := range vec {
			vec[j] = rng.Float32()
		}
		points[i] = &qdrant.PointStruct{
			Id:      qdrant.NewIDNum(uint64(i)),
			Vectors: qdrant.NewVectors(vec...),
			Payload: qdrant.NewValueMap(map[string]any{
				"category": fmt.Sprintf("c%d", i%3),
				"price":    float64(i) * 9.99,
			}),
		}
	}
	wait := true
	upResp, err := client.Upsert(ctx, &qdrant.UpsertPoints{
		CollectionName: collection,
		Points:         points,
		Wait:           &wait,
	})
	must(err)
	fmt.Printf("upsert: status=%v op_id=%d\n", upResp.GetStatus(), upResp.GetOperationId())

	// 4. Query points + measure latency
	qRng := rand.New(rand.NewSource(99))
	qVec := make([]float32, 8)
	for j := range qVec {
		qVec[j] = qRng.Float32()
	}
	t0 := time.Now()
	res, err := client.Query(ctx, &qdrant.QueryPoints{
		CollectionName: collection,
		Query:          qdrant.NewQuery(qVec...),
		Limit:          qdrant.PtrOf(uint64(3)),
		WithPayload:    qdrant.NewWithPayload(true),
	})
	must(err)
	wall := time.Since(t0)
	fmt.Println("\n=== Go: query results ===")
	for _, r := range res {
		fmt.Printf("  id=%v score=%.4f payload=%v\n",
			r.GetId().GetNum(), r.GetScore(), r.GetPayload())
	}
	fmt.Printf("wall=%.2f ms\n", float64(wall.Microseconds())/1000.0)
}

func must(err error) {
	if err != nil {
		panic(err)
	}
}
